def up(cursor, bot):
    cursor.execute("DROP TABLE prediction_run, prediction_run_entry")
