def up(cursor, bot):
    # Creating missed constraints:
    # banphrase_data
    cursor.execute('ALTER TABLE banphrase_data ADD FOREIGN KEY (added_by) REFERENCES "user"(id) ON DELETE SET NULL')
    cursor.execute('ALTER TABLE banphrase_data ADD FOREIGN KEY (edited_by) REFERENCES "user"(id) ON DELETE SET NULL')

    # command_data
    # In case you run into issues where this foreign key cannot be added because a referenced user does not exist, you can run the following query:
    #   UPDATE command_data SET added_by = NULL WHERE NOT EXISTS( SELECT 1 FROM "user" WHERE command_data.added_by = "user".id  );
    # It will update all rows where added_by references a non-exitant user and set the added_by value to NULL
    cursor.execute('ALTER TABLE command_data ADD FOREIGN KEY (added_by) REFERENCES "user"(id) ON DELETE SET NULL')
    # In case you run into issues where this foreign key cannot be added because a referenced user does not exist, you can run the following query:
    #   UPDATE command_data SET edited_by = NULL WHERE NOT EXISTS( SELECT 1 FROM "user" WHERE command_data.edited_by = "user".id  );
    # It will update all rows where edited_by references a non-exitant user and set the added_by value to NULL
    cursor.execute('ALTER TABLE command_data ADD FOREIGN KEY (edited_by) REFERENCES "user"(id) ON DELETE SET NULL')

    # pleblist_song
    cursor.execute("ALTER TABLE pleblist_song ADD FOREIGN KEY (stream_id) REFERENCES stream(id) ON DELETE CASCADE")
    cursor.execute('ALTER TABLE pleblist_song ADD FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE SET NULL')

    # prediction_run_entry
    cursor.execute(
        "ALTER TABLE prediction_run_entry ADD FOREIGN KEY (prediction_run_id) REFERENCES prediction_run(id) ON DELETE CASCADE"
    )
    cursor.execute('ALTER TABLE prediction_run_entry ADD FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE')

    # roulette
    # In case you run into issues where this foreign key cannot be added because a referenced user does not exist, you can run the following query:
    #   DELETE FROM roulette WHERE NOT EXISTS( SELECT 1 FROM "user" WHERE roulette.user_id = "user".id  );
    # It will delete all roulette stats for users that don't exist
    cursor.execute('ALTER TABLE roulette ADD FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE')

    # stream_chunk
    cursor.execute("ALTER TABLE stream_chunk ADD FOREIGN KEY (stream_id) REFERENCES stream(id) ON DELETE CASCADE")

    # Altering existing constraints to include ON DELETE statements:
    # command_example
    cursor.execute(
        "ALTER TABLE command_example DROP CONSTRAINT command_example_command_id_fkey, ADD FOREIGN KEY (command_id) REFERENCES command(id) ON DELETE CASCADE"
    )

    # hsbet_bet
    cursor.execute(
        'ALTER TABLE hsbet_bet DROP CONSTRAINT hsbet_bet_user_id_fkey, ADD FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE'
    )

    # prediction_run_entry
    cursor.execute(
        'ALTER TABLE prediction_run_entry DROP CONSTRAINT prediction_run_entry_user_id_fkey, ADD FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE'
    )

    # roulette
    cursor.execute(
        'ALTER TABLE roulette DROP CONSTRAINT roulette_user_id_fkey, ADD FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE'
    )

    # user_duel_stats
    cursor.execute(
        'ALTER TABLE user_duel_stats DROP CONSTRAINT user_duel_stats_user_id_fkey, ADD FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE'
    )
