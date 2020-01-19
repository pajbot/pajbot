import logging

log = logging.getLogger("pajbot")


def up(cursor, bot):
    # new: twitch_tier record
    cursor.execute('ALTER TABLE "user_connections" ADD COLUMN twitch_tier INTEGER DEFAULT NULL')
