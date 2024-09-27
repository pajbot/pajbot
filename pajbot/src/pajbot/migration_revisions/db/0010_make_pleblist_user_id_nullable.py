# In release version 1.38, there was a bug with 0004_unify_user_model that would cause pleblist_song rows to be
# deleted entirely if the referenced user (pleblist_song.user_id) was deleted. Instead, it was intended that on
# those rows, user_id be nullable, and the user_id be set to NULL on delete of the referenced user.

# Users that migrated their databases using version 1.38 are now in a database state where the foreign key constraints
# and NOT NULL constraint need to be corrected.
# For users that come from <=1.37 and upgrade using a bot of version >=1.39 will not encounter this problem,
# because the issue with 0004_unify_user_model has been corrected in 1.39.

# We could also have left 0004_unify_user_model untouched (keeping the bug), which would have eliminated the
# need for the additional conditional migration below. We decided to modify 0004_unify_user_model instead,
# so users running this migration in the future will not lose their pleblist_song rows and then will have to run
# an extensive recovery routine to restore the lost rows. This way, only users who ran the bugged version of
# 0004_unify_user_model will have to recover any deleted rows.

# The conditional migration below first checks whether the database was migrated using the "bugged" or "fixed"
# version of 0004_unify_user_model, and then executes the necessary schema changes to prepare the database for
# a restore of the lost data.

# Also see Pull Request #596: https://github.com/pajbot/pajbot/pull/596


def up(cursor, bot):
    # This query selects the "NOT NULL" state of the pleblist_song.user_id column, which we can use
    # to determine whether this database was migrated with the bugged or fixed version of 0004_unify_user_model
    cursor.execute(
        """
    SELECT attnotnull
    FROM pg_attribute
    WHERE
        attrelid = 'pleblist_song'::regclass
        AND attname = 'user_id'
    """
    )
    pleblist_song_user_id_column_unnullable = cursor.fetchone()[0]

    # If the column is marked NOT NULL, then the database was migrated with the bugged version of 0004_unify_user_model.
    if pleblist_song_user_id_column_unnullable:
        # Remove pleblist_song.user_id foreign key
        cursor.execute("ALTER TABLE pleblist_song DROP CONSTRAINT pleblist_song_user_id_fkey")

        # Make pleblist_song.user_id column nullable
        cursor.execute("ALTER TABLE pleblist_song ALTER COLUMN user_id DROP NOT NULL")

        # Re-add pleblist_song.user_id foreign key, with ON DELETE SET NULL (instead of ON DELETE CASCADE like before)
        cursor.execute('ALTER TABLE pleblist_song ADD FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE SET NULL')
