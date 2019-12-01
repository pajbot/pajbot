def up(cursor, bot):
    # The trigger was previously set to run AFTER UPDATE, we want it to run BEFORE UPDATE though to be correct.
    # Running the trigger AFTER the update means the data changes we wanted to have take place never took place.
    # The return value/modified row created inside the trigger procedure was ignored entirely.
    # In order for changes to the "NEW" row to actually be included in the update, we have to run BEFORE.
    # We just drop it and re-create it properly to fix our previous mistake here.
    cursor.execute('DROP TRIGGER user_login_update ON "user"')
    cursor.execute(
        """
    CREATE TRIGGER user_login_update
    BEFORE UPDATE OF login ON "user"
    FOR EACH ROW EXECUTE PROCEDURE trigger_user_update_login_last_updated()
    """
    )
