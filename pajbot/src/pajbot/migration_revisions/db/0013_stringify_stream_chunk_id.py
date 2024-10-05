def up(cursor, bot):
    cursor.execute("ALTER TABLE stream_chunk ALTER COLUMN broadcast_id TYPE TEXT")
