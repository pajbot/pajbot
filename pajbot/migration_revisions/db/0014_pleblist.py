import logging

log = logging.getLogger("pajbot")


def up(cursor, bot):
    cursor.execute('ALTER TABLE "pleblist_song" DROP COLUMN stream_id')

    # new: tier record
    cursor.execute('ALTER TABLE "pleblist_song" ADD COLUMN date_finished TIMESTAMPTZ DEFAULT NULL')
