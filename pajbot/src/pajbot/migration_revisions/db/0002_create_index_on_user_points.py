def up(cursor, bot):
    # the index on user(points) caches/indexes the table, ordered by points
    # so queries like the top 30 point farmers can skip sorting the entire
    # user table by points, and just instead use the sorting given by the
    # user(points) index.

    # e.g. compare (before and after creating the index):

    # without an index on points:
    #
    # pajbot=> EXPLAIN ANALYZE SELECT * FROM "user" ORDER BY points LIMIT 10;
    #                                                       QUERY PLAN
    # -----------------------------------------------------------------------------------------------------------------------
    #  Limit  (cost=1610.93..1610.96 rows=10 width=41) (actual time=12.005..12.009 rows=10 loops=1)
    #    ->  Sort  (cost=1610.93..1705.84 rows=37961 width=41) (actual time=12.003..12.004 rows=10 loops=1)
    #          Sort Key: points
    #          Sort Method: top-N heapsort  Memory: 27kB
    #          ->  Seq Scan on "user"  (cost=0.00..790.61 rows=37961 width=41) (actual time=0.030..7.097 rows=37961 loops=1)
    #  Planning Time: 0.187 ms
    #  Execution Time: 12.039 ms
    # (7 rows)

    # creating the index...
    #
    # pajbot=> CREATE INDEX ON "user"(points);
    # CREATE INDEX

    # now with the index!
    #
    # pajbot=> EXPLAIN ANALYZE SELECT * FROM "user" ORDER BY points LIMIT 10;
    #                                                               QUERY PLAN
    # ---------------------------------------------------------------------------------------------------------------------------------------
    #  Limit  (cost=0.29..0.59 rows=10 width=41) (actual time=0.041..0.050 rows=10 loops=1)
    #    ->  Index Scan using user_points_idx on "user"  (cost=0.29..1135.63 rows=37961 width=41) (actual time=0.038..0.046 rows=10 loops=1)
    #  Planning Time: 0.408 ms
    #  Execution Time: 0.071 ms
    # (4 rows)

    # notice the DB no longer sorts the users table, and query execution times have improved dramatically!
    cursor.execute('CREATE INDEX ON "user"(points)')
