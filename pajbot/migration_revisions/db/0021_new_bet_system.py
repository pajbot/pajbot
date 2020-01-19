import logging

log = logging.getLogger("pajbot")


def up(cursor, bot):
    cursor.execute("DROP TABLE IF EXISTS bet_game CASCADE")
    cursor.execute("DROP TABLE IF EXISTS bet_bet CASCADE")
    cursor.execute("DROP TYPE IF EXISTS bet_outcome CASCADE")
    cursor.execute("CREATE TYPE bet_outcome AS ENUM ('win','loss');")
    cursor.execute(
        """
    CREATE TABLE bet_game (
        id SERIAL PRIMARY KEY NOT NULL,
        timestamp timestamp with time zone,
        outcome bet_outcome,
        bets_closed BOOLEAN
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE bet_bet (
        game_id INT PRIMARY KEY NOT NULL REFERENCES "bet_game"(id) ON DELETE CASCADE,
        user_id TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
        timestamp timestamp with time zone,
        outcome bet_outcome NOT NULL,
        points INT NOT NULL,
        profit INT
    )
    """
    )
    cursor.execute("ALTER TABLE bet_bet DROP CONSTRAINT bet_bet_pkey")
    cursor.execute("ALTER TABLE bet_bet ADD PRIMARY KEY (game_id, user_id)")
