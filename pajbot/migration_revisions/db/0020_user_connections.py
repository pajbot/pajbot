import logging

log = logging.getLogger("pajbot")


def up(cursor, bot):
    cursor.execute('ALTER TABLE "user_connections" RENAME COLUMN twitch_tier TO discord_tier')
