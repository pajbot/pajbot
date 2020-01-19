import logging

log = logging.getLogger("pajbot")


def up(cursor, bot):
    # new: tier record
    cursor.execute('ALTER TABLE "playsound" ADD COLUMN cost integer DEFAULT NULL')
