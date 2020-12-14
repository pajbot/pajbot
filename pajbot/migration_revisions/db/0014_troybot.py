import logging

log = logging.getLogger("pajbot")


def up(cursor, bot):
    cursor.execute('ALTER TABLE "playsound" ADD COLUMN cost integer DEFAULT NULL ')
    cursor.execute('ALTER TABLE "playsound" ADD COLUMN tier INTEGER DEFAULT NULL')

    cursor.execute(
        """
    CREATE TABLE songrequest_song_info (
        video_id TEXT PRIMARY KEY NOT NULL,
        title TEXT NOT NULL,
        duration INT NOT NULL,
        default_thumbnail TEXT NOT NULL,
        banned boolean ,
        favourite boolean
    )
    """
    )
    cursor.execute(
        """
    CREATE TABLE songrequest_queue (
        id SERIAL PRIMARY KEY,
        video_id TEXT NOT NULL REFERENCES "songrequest_song_info"(video_id) ON DELETE CASCADE,
        date_added timestamp with time zone DEFAULT NULL,
        skip_after INT,
        requested_by_id TEXT REFERENCES "user"(id) ON DELETE CASCADE,
        date_resumed timestamp with time zone,
        played_for REAL NOT NULL DEFAULT 0
    )
    """
    )
    cursor.execute(
        """
    CREATE TABLE songrequest_history (
        id SERIAL PRIMARY KEY,
        stream_id INT,
        video_id TEXT NOT NULL REFERENCES "songrequest_song_info"(video_id) ON DELETE CASCADE,
        date_finished timestamp with time zone DEFAULT NULL,
        requested_by_id TEXT REFERENCES "user"(id) ON DELETE CASCADE,
        skipped_by_id TEXT REFERENCES "user"(id) ON DELETE CASCADE,
        skip_after INT
    )
    """
    )

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

    cursor.execute(
        """
    CREATE TABLE widgets (
        id SERIAL PRIMARY KEY NOT NULL,
        name TEXT NOT NULL
    )
    """
    )
    cursor.execute(
        """
    CREATE TABLE websockets (
        id SERIAL PRIMARY KEY NOT NULL,
        widget_id INT NOT NULL REFERENCES "widgets"(id) ON DELETE CASCADE,
        salt TEXT NOT NULL UNIQUE
    )
    """
    )
    cursor.execute("INSERT INTO widgets(id, name) VALUES (1, 'SHOWEMOTE')")
    cursor.execute("INSERT INTO widgets(id, name) VALUES (2, 'BETTING')")
    cursor.execute("INSERT INTO widgets(id, name) VALUES (3, 'PLAYSOUND')")
    cursor.execute("INSERT INTO widgets(id, name) VALUES (4, 'SONGREQUEST')")
    cursor.execute("INSERT INTO widgets(id, name) VALUES (5, 'EMOTECOMBO')")
    cursor.execute("INSERT INTO widgets(id, name) VALUES (6, 'TTS')")

    cursor.execute('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS tier INTEGER NOT NULL DEFAULT 0')

    cursor.execute('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS num_paid_timeouts INTEGER NOT NULL DEFAULT 0')
    cursor.execute('DROP MATERIALIZED VIEW user_rank')
    cursor.execute(
        """
    CREATE MATERIALIZED VIEW user_rank AS (
        SELECT
            id as user_id,
            RANK() OVER (ORDER BY points DESC) points_rank,
            RANK() OVER (ORDER BY num_lines DESC) num_lines_rank,
            RANK() OVER (ORDER BY num_paid_timeouts DESC) num_paid_timeouts_rank
        FROM "user"
    )
    """
    )
    cursor.execute("CREATE UNIQUE INDEX ON user_rank(user_id)")
