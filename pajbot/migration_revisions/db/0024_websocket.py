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
    cursor.execute("INSERT INTO widgets(id, name) VALUES (1, 'SHOWEMOTE')")
    cursor.execute("INSERT INTO widgets(id, name) VALUES (2, 'BETTING')")
    cursor.execute("INSERT INTO widgets(id, name) VALUES (3, 'PLAYSOUND')")
    cursor.execute("INSERT INTO widgets(id, name) VALUES (4, 'SONGREQUEST')")
