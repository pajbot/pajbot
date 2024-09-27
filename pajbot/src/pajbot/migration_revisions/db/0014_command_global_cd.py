def up(cursor, bot):
    # new: command.use_global_cd
    cursor.execute("ALTER TABLE command ADD COLUMN use_global_cd BOOLEAN NOT NULL DEFAULT FALSE")
