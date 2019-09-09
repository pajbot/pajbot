def up(cursor, context):
    cursor.execute("CREATE INDEX ON \"user\"(points)")
