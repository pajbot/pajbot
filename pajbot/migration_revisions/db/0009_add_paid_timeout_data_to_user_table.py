def up(cursor, bot):
    cursor.execute('ALTER TABLE "user" ADD COLUMN timeout_end TIMESTAMPTZ DEFAULT NULL')
