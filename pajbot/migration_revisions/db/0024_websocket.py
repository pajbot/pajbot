import logging

log = logging.getLogger("pajbot")


def up(cursor, bot):
    cursor.execute(
        """
    CREATE TABLE widgets (
        id SERIAL PRIMARY KEY NOT NULL,
        name TEXT NOT NULL
    )
    """
    )
    cursor.execute(
        """
    CREATE TABLE websockets (
        id SERIAL PRIMARY KEY NOT NULL,
        widget_id INT NOT NULL REFERENCES "widgets"(id) ON DELETE CASCADE,
        salt TEXT NOT NULL UNIQUE
    )
    """
    )
