def up(cursor, bot):
    cursor.execute('ALTER TABLE "user" ADD COLUMN founder BOOLEAN NOT NULL DEFAULT FALSE')
    cursor.execute('ALTER TABLE "user" ADD COLUMN vip BOOLEAN NOT NULL DEFAULT FALSE')
    # fixes poor-ish performance in VIP and moderators refresh
    cursor.execute('CREATE INDEX ON "user"(vip)')
    cursor.execute('CREATE INDEX ON "user"(moderator)')
