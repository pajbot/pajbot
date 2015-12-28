import logging
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import inspect

Base = declarative_base()

log = logging.getLogger('pajbot')


class DBManager:
    def init(url):
        DBManager.engine = create_engine(url)
        DBManager.Session = sessionmaker(bind=DBManager.engine)

    def create_session(**options):
        """
        Useful options:
        expire_on_commit=False
        """

        try:
            return DBManager.Session(**options)
        except:
            log.exception('Unhandled exception while creating a session')

        return None

    def session_add_expunge(object, **options):
        """
        Useful shorthand method of creating a session,
        adding an object to the session,
        committing,
        expunging the object,
        closing the session,
        all while having expire_on_commit set to False
        """

        if 'expire_on_commit' not in options:
            options['expire_on_commit'] = False

        session = DBManager.create_session(**options)
        try:
            session.add(object)
            session.commit()
            session.expunge(object)
        except:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def create_session_scope(**options):
        session = DBManager.create_session(**options)
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def debug(object):
        try:
            inspected_object = inspect(object)
            log.debug('Object:     {0}'.format(object))
            log.debug('Transient:  {0.transient}'.format(inspected_object))
            log.debug('Pending:    {0.pending}'.format(inspected_object))
            log.debug('Persistent: {0.persistent}'.format(inspected_object))
            log.debug('Detached:   {0.detached}'.format(inspected_object))
        except:
            log.exception('Uncaught exception in DBManager.debug')
