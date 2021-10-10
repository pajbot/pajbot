from __future__ import annotations

from typing import TYPE_CHECKING, Iterator, Optional

import logging
from contextlib import contextmanager

import sqlalchemy
from psycopg2.extensions import STATUS_IN_TRANSACTION
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, scoped_session, sessionmaker

if TYPE_CHECKING:
    from psycopg2 import connection as Psycopg2Connection


Base = declarative_base()

log = logging.getLogger("pajbot")


class ServerNoticeLogger:
    def append(self, notice: str) -> None:
        # notice is stripped of whitespace since it usually ends in a newline
        # These are notices like "NOTICE:  relation "schema_version" already exists, skipping",
        # but they can also be warnings, etc.
        log.info(f"PostgreSQL Server notice: {notice.strip()}")


class DBManager:
    engine: Optional[sqlalchemy.engine.base.Engine] = None
    _sessionmaker: Optional[sessionmaker] = None
    ScopedSession: Optional[scoped_session] = None

    @staticmethod
    def init(url: str) -> None:
        DBManager.engine = create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20)

        # https://docs.sqlalchemy.org/en/13/core/events.html#sqlalchemy.events.PoolEvents.connect
        @event.listens_for(DBManager.engine, "connect")
        def on_connect(dbapi_connection, connection_record) -> None:
            # http://initd.org/psycopg/docs/connection.html#connection.notices
            # > The notices attribute is writable: the user may replace it with any Python object
            # > exposing an append() method. If appending raises an exception the notice is silently dropped.
            # This replaces the list object with a logger that logs the incoming notices
            dbapi_connection.notices = ServerNoticeLogger()

        DBManager._sessionmaker = sessionmaker(bind=DBManager.engine, autoflush=False)
        DBManager.ScopedSession = scoped_session(sessionmaker(bind=DBManager.engine))

    @staticmethod
    def create_session(**options) -> Session:
        """
        Useful options:
        expire_on_commit=False
        """

        if DBManager._sessionmaker is None:
            raise ValueError("DBManager not initialized")

        return DBManager._sessionmaker(**options)

    @staticmethod
    def create_scoped_session(**options) -> Session:
        """
        Useful options:
        expire_on_commit=False
        """

        if DBManager.ScopedSession is None:
            raise ValueError("DBManager not initialized")

        return DBManager.ScopedSession(**options)

    @staticmethod
    def session_add_expunge(db_object, **options) -> None:
        """
        Useful shorthand method of creating a session,
        adding an object to the session,
        committing,
        expunging the object,
        closing the session,
        all while having expire_on_commit set to False
        """

        if "expire_on_commit" not in options:
            options["expire_on_commit"] = False

        session = DBManager.create_session(**options)
        try:
            session.add(db_object)
            session.commit()
            session.expunge(db_object)
        except:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    @contextmanager
    def create_session_scope(**options) -> Iterator[Session]:
        session = DBManager.create_session(**options)
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    @contextmanager
    def create_session_scope_nc(**options):
        session = DBManager.create_session(**options)
        try:
            yield session
        except:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    @contextmanager
    def create_session_scope_ea(**options):
        session = DBManager.create_session(**options)
        try:
            yield session
            session.expunge_all()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    @contextmanager
    def create_scoped_session_scope(**options):
        session = DBManager.create_scoped_session(**options)
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    @contextmanager
    def create_dbapi_connection_scope(autocommit=False) -> Iterator[Psycopg2Connection]:
        if DBManager.engine is None:
            raise ValueError("DBManager not initialized")

        # This method's contextmanager just checks the connection out, sets autocommit if desired, and
        # returns the connection to the pool when the contextmanager exits
        # It does not perform transaction control! create_dbapi_session_scope is more useful since it provides
        # an automatic COMMIT/ROLLBACK mechanism, and also returns a DBAPI Session instead of Connection.

        # https://docs.sqlalchemy.org/en/13/core/connections.html#sqlalchemy.engine.Engine.raw_connection
        pool_connection = DBManager.engine.raw_connection()

        # Quoting from the SQLAlchemy docs:
        # > The returned object is a proxied version of the DBAPI connection object used by the underlying driver in use.
        # To be able to use the connection as a contextmanager for transaction control,
        # we need the actual underlying connection, the SQLAlchemy proxy will not work for this.
        raw_connection = pool_connection.connection

        try:
            if autocommit:
                # The parameter "pool_pre_ping=True" from create_engine() above makes SQLAlchemy issue a
                # "SELECT 1" to test the connection works before returning it from the connection pool.
                # Even the simple "SELECT 1" has automatically begun a transaction, and the connection
                # will now be "idle in transaction".
                #
                # Because we can only enable autocommit on "idle" connections, we need to ROLLBACK if a transaction
                # is ongoing first:
                if raw_connection.status == STATUS_IN_TRANSACTION:
                    raw_connection.rollback()
                # http://initd.org/psycopg/docs/connection.html#connection.autocommit
                raw_connection.autocommit = True

            try:
                yield raw_connection
            finally:
                # We want to reset the connection to a clean state in the end, so we don't return connections
                # to the pool that are in an ongoing transaction, or whose transaction is aborted
                # (typical error message: "ERROR: current transaction is aborted,
                # commands ignored until end of transaction block")
                if raw_connection.status == STATUS_IN_TRANSACTION:
                    raw_connection.rollback()
        finally:
            if autocommit:
                # Because the connection is returned to the pool, we want to reset the autocommit state on it
                raw_connection.autocommit = False

            # Finally release connection back to the pool (notice we use .close() on the pool connection,
            # not raw_connection which would close the connection for good)
            pool_connection.close()

    @staticmethod
    @contextmanager
    def create_dbapi_cursor_scope(autocommit=False):
        # The create_dbapi_connection_scope context manager just does basic setup/cleanup of resources,
        # not transaction control
        with DBManager.create_dbapi_connection_scope(autocommit=autocommit) as sql_conn:
            if autocommit:
                # Using the cursor as a context manager just does cleanup on the resources of the cursor,
                # it does not perform transaction control with BEGIN/COMMIT/ROLLBACK.
                with sql_conn.cursor() as cursor:
                    yield cursor
            else:
                # Using the connection as a context manager however gives us BEGIN/COMMIT/ROLLBACK transaction control.
                # The connection is automatically COMMITed should the inner block return without an exception,
                # or the connection is ROLLBACKed if an exception occurs.
                with sql_conn:
                    # Now use cursor as context manager, to release resources correctly
                    with sql_conn.cursor() as cursor:
                        yield cursor

    @staticmethod
    def debug(raw_object: object) -> None:
        try:
            inspected_object = inspect(raw_object)
            log.debug(f"Object:     {raw_object}")
            log.debug(f"Transient:  {inspected_object.transient}")
            log.debug(f"Pending:    {inspected_object.pending}")
            log.debug(f"Persistent: {inspected_object.persistent}")
            log.debug(f"Detached:   {inspected_object.detached}")
        except:
            log.exception("Uncaught exception in DBManager.debug")
