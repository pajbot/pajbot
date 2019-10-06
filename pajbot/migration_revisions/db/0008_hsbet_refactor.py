def up(cursor, bot):
    # Useful query for deleting duplicate games:
    # DELETE FROM hsbet_game a WHERE a.ctid <> (SELECT min(b.ctid) FROM hsbet_game b WHERE a.internal_id = b.internal_id);

    # hsbet_game.internal_id -> trackobot_id, +UNIQUE, -NOT NULL
    cursor.execute("ALTER TABLE hsbet_game RENAME COLUMN internal_id TO trackobot_id")
    cursor.execute("ALTER TABLE hsbet_game ALTER COLUMN trackobot_id DROP NOT NULL")
    cursor.execute("ALTER TABLE hsbet_game ADD UNIQUE(trackobot_id)")

    # new: hsbet_game.bet_deadline
    cursor.execute("ALTER TABLE hsbet_game ADD COLUMN bet_deadline TIMESTAMPTZ")

    # hsbet_game.outcome: -NOT NULL
    cursor.execute("ALTER TABLE hsbet_game ALTER COLUMN outcome DROP NOT NULL")

    # hsbet_game: Check that either both trackobot_id and outcome are NULL, or both are not.
    cursor.execute(
        "ALTER TABLE hsbet_game ADD CHECK ((trackobot_id IS NULL AND outcome is NULL) OR (trackobot_id IS NOT NULL AND outcome is NOT NULL))"
    )

    # hsbet_game.game_id: add ON DELETE CASCADE
    cursor.execute("ALTER TABLE hsbet_bet DROP CONSTRAINT hsbet_bet_game_id_fkey")
    cursor.execute("ALTER TABLE hsbet_bet ADD FOREIGN KEY (game_id) REFERENCES hsbet_game(id) ON DELETE CASCADE")

    # hsbet_game: Remove id column, add combined primary key
    cursor.execute("ALTER TABLE hsbet_bet DROP CONSTRAINT hsbet_bet_pkey")
    cursor.execute("ALTER TABLE hsbet_bet DROP COLUMN id")
    cursor.execute("ALTER TABLE hsbet_bet ADD PRIMARY KEY (game_id, user_id)")

    # hsbet_game.profit: -NOT NULL
    cursor.execute("ALTER TABLE hsbet_bet ALTER COLUMN profit DROP NOT NULL")
