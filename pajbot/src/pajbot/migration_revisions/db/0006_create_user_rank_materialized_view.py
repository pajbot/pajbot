def up(cursor, bot):
    cursor.execute(
        """
    CREATE MATERIALIZED VIEW user_rank AS (
        SELECT
            id as user_id,
            RANK() OVER (ORDER BY points DESC) points_rank,
            RANK() OVER (ORDER BY num_lines DESC) num_lines_rank
        FROM "user"
    )
    """
    )
    cursor.execute("CREATE UNIQUE INDEX ON user_rank(user_id)")
