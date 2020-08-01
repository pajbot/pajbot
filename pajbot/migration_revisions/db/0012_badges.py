def up(cursor, bot):
    cursor.execute('ALTER TABLE "user" ADD COLUMN founder BOOLEAN NOT NULL DEFAULT FALSE')
    cursor.execute('ALTER TABLE "user" ADD COLUMN vip BOOLEAN NOT NULL DEFAULT FALSE')
    cursor.execute('ALTER TABLE "user" ADD COLUMN broadcaster BOOLEAN NOT NULL DEFAULT FALSE')
