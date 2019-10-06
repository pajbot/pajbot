from contextlib import contextmanager


class DatabaseMigratable:
    def __init__(self, conn):
        self.conn = conn

    @contextmanager
    def create_resource(self):
        # http://initd.org/psycopg/docs/usage.html#with-statement
        with self.conn:  # transaction control, does NOT close the connection
            with self.conn.cursor() as cursor:  # auto resource release of cursor
                cursor.execute("CREATE TABLE IF NOT EXISTS schema_version(revision_id INT NOT NULL)")
                yield cursor

    def get_current_revision(self, cursor):
        cursor.execute("SELECT revision_id FROM schema_version")
        row = cursor.fetchone()
        if row is not None:
            return row[0]
        else:
            return None

    def set_revision(self, cursor, id):
        cursor.execute("DELETE FROM schema_version")
        cursor.execute("INSERT INTO schema_version(revision_id) VALUES (%s)", (id,))

    @staticmethod
    def describe_resource():
        return "db"
