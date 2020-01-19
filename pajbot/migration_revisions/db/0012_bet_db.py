import logging

log = logging.getLogger("pajbot")


def up(cursor, bot):
    cursor.execute(
        """
    CREATE TYPE bet_outcome AS
    (
        win text,
        loss text
    )
    """
    )
    cursor.execute(
        """
    CREATE TABLE bet_game
    (
        id integer NOT NULL,
        internal_id time with time zone,
        outcome bet_outcome,
        win_bettors integer,
        loss_bettors integer,
        CONSTRAINT bet_game_pkey PRIMARY KEY (id)
    )
    """
    )
