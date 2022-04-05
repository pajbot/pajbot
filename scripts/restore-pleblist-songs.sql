\set ON_ERROR_STOP on

BEGIN;

-- This is the table format of the table, pre-user-model-migration (This is what the backup is of)
CREATE TEMPORARY TABLE pleblist_song_old
(
    id          integer                  NOT NULL,
    stream_id   integer                  NOT NULL,
    youtube_id  text                     NOT NULL,
    date_added  timestamp with time zone NOT NULL,
    date_played timestamp with time zone,
    skip_after  integer,
    user_id     integer
) ON COMMIT DROP;

-- We need the old user data so we can cross reference old user IDs with new user IDs
CREATE TEMPORARY TABLE user_old
(
    id                      integer NOT NULL,
    username                text    NOT NULL,
    username_raw            text,
    level                   integer NOT NULL,
    points                  integer NOT NULL,
    subscriber              boolean NOT NULL,
    minutes_in_chat_online  integer NOT NULL,
    minutes_in_chat_offline integer NOT NULL
) ON COMMIT DROP;

-- Read the "COPY" dumps
\copy pleblist_song_old FROM 'pleblist_song_old.txt';
\copy user_old FROM 'user_old.txt';

INSERT INTO pleblist_song(id, stream_id, youtube_id, date_added, date_played, skip_after, user_id)
SELECT pleblist_song_old.id,
       pleblist_song_old.stream_id,
       pleblist_song_old.youtube_id,
       pleblist_song_old.date_added,
       pleblist_song_old.date_played,
       pleblist_song_old.skip_after,
       user_new.id AS user_id
FROM pleblist_song_old
    -- Cross reference old user IDs to new user IDs, where possible
         LEFT JOIN user_old ON user_old.id = pleblist_song_old.user_id
         LEFT JOIN "user" user_new ON user_old.username = user_new.login
    -- Filter out rows that already exist in the new pleblist song table
         LEFT JOIN pleblist_song pleblist_song_new ON pleblist_song_old.id = pleblist_song_new.id
WHERE pleblist_song_new.id IS NULL;

COMMIT;
