import logging

log = logging.getLogger("pajbot")


def up(cursor, bot):
    cursor.execute("DROP TABLE IF EXISTS songrequest_queue")
    cursor.execute("DROP TABLE IF EXISTS songrequest_history")
    cursor.execute("DROP TABLE IF EXISTS songrequest_song_info")
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
        queue INT NOT NULL,
        video_id TEXT NOT NULL REFERENCES "songrequest_song_info"(video_id) ON DELETE CASCADE,
        date_added timestamp with time zone DEFAULT NULL,
        skip_after INT,
        playing BOOLEAN,
        requested_by_id TEXT REFERENCES "user"(id) ON DELETE CASCADE,
        current_song_time REAL NOT NULL DEFAULT 0
    )
    """
    )
    cursor.execute(
        """
    CREATE TABLE songrequest_history (
        id SERIAL PRIMARY KEY,
        stream_id INT NOT NULL,
        video_id TEXT NOT NULL REFERENCES "songrequest_song_info"(video_id) ON DELETE CASCADE,
        date_finished timestamp with time zone DEFAULT NULL,
        requested_by_id TEXT REFERENCES "user"(id) ON DELETE CASCADE,
        skipped_by_id TEXT REFERENCES "user"(id) ON DELETE CASCADE,
        skip_after INT
    )
    """
    )
