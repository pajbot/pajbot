import logging

log = logging.getLogger("pajbot")


def up(cursor, bot):
    cursor.execute('ALTER TABLE "user_connections" ADD COLUMN twitch_tier INTEGER DEFAULT NULL')
