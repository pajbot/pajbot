from __future__ import annotations

from typing import TYPE_CHECKING, Iterator, Optional

from contextlib import contextmanager

if TYPE_CHECKING:
    from psycopg2 import connection as Psycopg2Connection
    from psycopg2 import cursor as Psycopg2Cursor


class DatabaseMigratable:
    def __init__(self, conn: Psycopg2Connection) -> None:
        self.conn = conn

    @contextmanager
    def create_resource(self) -> Iterator[Psycopg2Cursor]:
        # http://initd.org/psycopg/docs/usage.html#with-statement
        with self.conn:  # transaction control, does NOT close the connection
            with self.conn.cursor() as cursor:  # auto resource release of cursor
                cursor.execute("CREATE TABLE IF NOT EXISTS schema_version(revision_id INT NOT NULL)")
                yield cursor

    def get_current_revision(self, cursor: Psycopg2Cursor) -> Optional[int]:
        cursor.execute("SELECT revision_id FROM schema_version")
        row = cursor.fetchone()
        if row is not None:
            return int(row[0])
        else:
            return None

    def set_revision(self, cursor: Psycopg2Cursor, id: int) -> None:
        cursor.execute("DELETE FROM schema_version")
        cursor.execute("INSERT INTO schema_version(revision_id) VALUES (%s)", (id,))

    @staticmethod
    def describe_resource() -> str:
        return "db"
