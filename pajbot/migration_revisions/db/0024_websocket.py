import logging

log = logging.getLogger("pajbot")


def up(cursor, bot):
    cursor.execute(
        """
    CREATE TABLE websockets (
        id SERIAL PRIMARY KEY NOT NULL,
        salt TEXT NOT NULL UNIQUE
    )
    """
    )
