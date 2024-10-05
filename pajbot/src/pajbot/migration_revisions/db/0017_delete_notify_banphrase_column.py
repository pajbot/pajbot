def up(cursor, bot):
    cursor.execute("ALTER TABLE banphrase DROP COLUMN notify")
