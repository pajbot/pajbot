def up(cursor, bot):
    # for the mass ping module check, it uses a check like this:
    # SELECT count(*)
    # FROM "user"
    # WHERE "user".login IN ('word1', 'word2', 'word3') OR lower("user".name) IN ('word1', 'word2', 'word3')
    # so that query becomes much faster with an index on lower(name).
    cursor.execute('CREATE INDEX ON "user"(lower(name))')
