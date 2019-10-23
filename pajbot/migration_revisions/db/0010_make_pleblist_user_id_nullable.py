# This migration is here to correct a previous error in the 0004_unify_user_model migration, where the pleblist_song.user_id column was incorrectly marked as non-nullable


def up(cursor, bot):
    # This query selects the "unnullable" state of the pleblist_song.user_id column
    # We use this as a check for whether this schema has run migration 0004_unify_user_model in its non-fixed state, as that's what we're trying to remedy
    cursor.execute(
        """
    SELECT attnotnull
    FROM pg_attribute
    WHERE
        attrelid = 'pleblist_song'::regclass
    and attname = 'user_id'
    """
    )
    pleblist_song_user_id_column_unnullable = cursor.fetchone()[0]

    if pleblist_song_user_id_column_unnullable:
        # Remove pleblist_song.user_id foreign key
        cursor.execute("ALTER TABLE pleblist_song DROP CONSTRAINT pleblist_song_user_id_fkey")

        # Make pleblist_song.user_id column nullable
        cursor.execute("ALTER TABLE pleblist_song ALTER COLUMN user_id DROP NOT NULL")

        # Re-add pleblist_song.user_id foreign key
        cursor.execute(
            'ALTER TABLE pleblist_song ADD FOREIGN KEY (user_id) REFERENCES "user"(twitch_id) ON DELETE SET NULL'
        )
