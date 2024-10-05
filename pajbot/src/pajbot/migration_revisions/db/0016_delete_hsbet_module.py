def up(cursor, bot):
    cursor.execute("DROP TABLE hsbet_game, hsbet_bet")
    cursor.execute("DROP TYPE hsbet_outcome")
