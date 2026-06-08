def up(cursor, bot):
    cursor.execute('ALTER TABLE "user" ADD COLUMN long_timeout_end TIMESTAMPTZ DEFAULT NULL')
