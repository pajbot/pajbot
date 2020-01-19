import logging

log = logging.getLogger("pajbot")


def up(cursor, bot):
    # new: twitch_tier record
    cursor.execute("DROP TABLE user_connections")

    cursor.execute(
        """
    CREATE TABLE user_connections (
        twitch_id TEXT PRIMARY KEY NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
        twitch_login TEXT DEFAULT NULL,
        discord_user_id TEXT UNIQUE,
        steam_id TEXT UNIQUE,
        discord_username TEXT
    )
    """
    )
