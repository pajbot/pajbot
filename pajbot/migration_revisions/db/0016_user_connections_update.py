import logging

log = logging.getLogger("pajbot")


def up(cursor, bot):
    cursor.execute('ALTER TABLE "user_connections" ADD COLUMN twitch_login text DEFAULT NULL')
    cursor.execute(
        """
        ALTER TABLE "user_connections"
        ADD CONSTRAINT "Twitch ID" FOREIGN KEY (twitch_id)
            REFERENCES "user" (id) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION
            NOT VALID
        """
    )
