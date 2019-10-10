from contextlib import contextmanager

import json

import datetime

from retry.api import retry_call
from tqdm import tqdm

from pajbot.managers.redis import RedisManager


def up(cursor, bot):
    redis = RedisManager.get()

    # new: twitch_id (will be renamed to "id" after the migration below...)
    cursor.execute('ALTER TABLE "user" ADD COLUMN twitch_id TEXT')  # nullable for now. Will be NOT NULL later
    cursor.execute('CREATE UNIQUE INDEX ON "user"(twitch_id)')

    # username -> login
    cursor.execute('ALTER TABLE "user" RENAME COLUMN username TO login')
    cursor.execute("DROP INDEX user_username_idx")  # UNIQUE
    cursor.execute('ALTER TABLE "user" DROP CONSTRAINT user_username_key')  # PRIMARY KEY
    cursor.execute('CREATE INDEX ON "user"(login)')  # create a new index, non-unique

    # username_raw -> name
    cursor.execute('ALTER TABLE "user" RENAME COLUMN username_raw TO name')

    # level: add default
    cursor.execute('ALTER TABLE "user" ALTER COLUMN level SET DEFAULT 100')

    # points: add default
    cursor.execute('ALTER TABLE "user" ALTER COLUMN points SET DEFAULT 0')

    # subscriber: add default
    cursor.execute('ALTER TABLE "user" ALTER COLUMN subscriber SET DEFAULT FALSE')

    # points: INT -> BIGINT
    cursor.execute('ALTER TABLE "user" ALTER COLUMN points SET DATA TYPE BIGINT')

    # new: moderator
    cursor.execute('ALTER TABLE "user" ADD COLUMN moderator BOOLEAN NOT NULL DEFAULT FALSE')

    # new: num_lines
    cursor.execute('ALTER TABLE "user" ADD COLUMN num_lines BIGINT NOT NULL DEFAULT 0')
    cursor.execute('CREATE INDEX ON "user"(num_lines)')  # same reason as in 0002_create_index_on_user_points.py

    def safe_to_int(input):
        try:
            return int(input)
        except ValueError:
            return None

    for login, num_lines in redis.zscan_iter(f"{bot.streamer}:users:num_lines", score_cast_func=safe_to_int):
        if num_lines is None:
            # invalid amount in redis, skip
            continue
        cursor.execute('UPDATE "user" SET num_lines = %s WHERE login = %s', (num_lines, login))

    # new: tokens
    cursor.execute('ALTER TABLE "user" ADD COLUMN tokens INT NOT NULL DEFAULT 0')
    for login, tokens in redis.zscan_iter(f"{bot.streamer}:users:tokens", score_cast_func=safe_to_int):
        if tokens is None:
            # invalid amount in redis, skip
            continue
        cursor.execute('UPDATE "user" SET tokens = %s WHERE login = %s', (tokens, login))

    # new: last_seen
    cursor.execute('ALTER TABLE "user" ADD COLUMN last_seen TIMESTAMPTZ DEFAULT NULL')
    for login, last_seen_raw in redis.hscan_iter(f"{bot.streamer}:users:last_seen"):
        last_seen = datetime.datetime.fromtimestamp(float(last_seen_raw), tz=datetime.timezone.utc)
        cursor.execute('UPDATE "user" SET last_seen = %s WHERE login = %s', (last_seen, login))

    # new: last_active
    cursor.execute('ALTER TABLE "user" ADD COLUMN last_active TIMESTAMPTZ DEFAULT NULL')
    for login, last_active_raw in redis.hscan_iter(f"{bot.streamer}:users:last_active"):
        last_seen = datetime.datetime.fromtimestamp(float(last_active_raw), tz=datetime.timezone.utc)
        cursor.execute('UPDATE "user" SET last_active = %s WHERE login = %s', (last_seen, login))

    # minutes_in_chat_{online,offline} -> INTERVAL type and renamed to time_in_chat_...
    cursor.execute('ALTER TABLE "user" RENAME COLUMN minutes_in_chat_online TO time_in_chat_online')
    cursor.execute('ALTER TABLE "user" RENAME COLUMN minutes_in_chat_offline TO time_in_chat_offline')
    cursor.execute(
        """
    ALTER TABLE "user" ALTER COLUMN time_in_chat_online SET DATA TYPE INTERVAL
    USING make_interval(mins := time_in_chat_online)
    """
    )
    cursor.execute(
        """
    ALTER TABLE "user" ALTER COLUMN time_in_chat_offline SET DATA TYPE INTERVAL
    USING make_interval(mins := time_in_chat_offline)
    """
    )
    cursor.execute("ALTER TABLE \"user\" ALTER COLUMN time_in_chat_online SET DEFAULT INTERVAL '0 minutes'")
    cursor.execute("ALTER TABLE \"user\" ALTER COLUMN time_in_chat_offline SET DEFAULT INTERVAL '0 minutes'")

    # new: ignored
    cursor.execute('ALTER TABLE "user" ADD COLUMN ignored BOOLEAN NOT NULL DEFAULT FALSE')
    for login in redis.hkeys(f"{bot.streamer}:users:ignored"):
        cursor.execute('UPDATE "user" SET ignored = TRUE WHERE login = %s', (login,))

    # new: banned
    cursor.execute('ALTER TABLE "user" ADD COLUMN banned BOOLEAN NOT NULL DEFAULT FALSE')
    for login in redis.hkeys(f"{bot.streamer}:users:banned"):
        cursor.execute('UPDATE "user" SET banned = TRUE WHERE login = %s', (login,))

    # note: username_raw is not migrated in from redis, since the username_raw data will be fetched
    # fresh from the Twitch API below anyways.

    # migrate users to ID
    cursor.execute('SELECT COUNT(*) FROM "user"')
    users_count = cursor.fetchone()[0]

    if users_count > 0:
        progress_bar = tqdm(total=users_count, unit="users")
        for offset in range(0, users_count, 100):
            cursor.execute('SELECT id, login FROM "user" ORDER BY id LIMIT 100 OFFSET %s FOR UPDATE', (offset,))
            rows = cursor.fetchall()  # = [(id, login), (id, login), (id, login), ...]

            usernames_to_fetch = [t[1] for t in rows]
            all_user_basics = retry_call(
                bot.twitch_helix_api.bulk_get_user_basics_by_login, fargs=[usernames_to_fetch], tries=3, delay=5
            )

            for id, basics in zip((t[0] for t in rows), all_user_basics):
                if basics is not None:
                    cursor.execute(
                        'UPDATE "user" SET twitch_id = %s, login = %s, name = %s WHERE id = %s',
                        (basics.id, basics.login, basics.name, id),
                    )
                progress_bar.update()

        progress_bar.close()

    # update admin logs to primary-key by Twitch ID.
    admin_logs_key = f"{bot.streamer}:logs:admin"
    all_admin_logs = redis.lrange(admin_logs_key, 0, -1)
    # all_admin_logs and new_log_entries are in newest -> oldest order
    new_log_entries = []
    for idx, raw_log_entry in enumerate(all_admin_logs):
        log_entry = json.loads(raw_log_entry)
        old_internal_id = log_entry["user_id"]
        cursor.execute('SELECT twitch_id FROM "user" WHERE id = %s', (old_internal_id,))
        row = cursor.fetchone()
        if row is not None and row[0] is not None:
            log_entry["user_id"] = row[0]
        else:
            log_entry["user_id"] = None
        new_log_entries.append(log_entry)

    @contextmanager
    def also_move_pkey(table, column):
        cursor.execute(f"ALTER TABLE {table} DROP CONSTRAINT {table}_pkey")
        yield
        cursor.execute(f"ALTER TABLE {table} ADD PRIMARY KEY ({column})")

    def update_foreign_key(table, column, nullable=False):
        cursor.execute(
            f"ALTER TABLE {table} DROP CONSTRAINT {table}_{column}_fkey, ALTER COLUMN {column} SET DATA TYPE TEXT"
        )
        if not nullable:
            cursor.execute(f"ALTER TABLE {table} ALTER COLUMN {column} DROP NOT NULL")
        cursor.execute(f'UPDATE {table} T SET {column} = (SELECT twitch_id FROM "user" WHERE id = T.{column}::int)')
        if not nullable:
            cursor.execute(f"DELETE FROM {table} WHERE {column} IS NULL")
            cursor.execute(f"ALTER TABLE {table} ALTER COLUMN {column} SET NOT NULL")

        if nullable:
            on_delete_action = "SET NULL"
        else:
            on_delete_action = "CASCADE"
        cursor.execute(
            f'ALTER TABLE {table} ADD FOREIGN KEY ({column}) REFERENCES "user"(twitch_id) ON DELETE {on_delete_action}'
        )

    update_foreign_key("banphrase_data", "added_by", nullable=True)
    update_foreign_key("banphrase_data", "edited_by", nullable=True)
    update_foreign_key("command_data", "added_by", nullable=True)
    update_foreign_key("command_data", "edited_by", nullable=True)
    update_foreign_key("hsbet_bet", "user_id")
    update_foreign_key("pleblist_song", "user_id")
    update_foreign_key("prediction_run_entry", "user_id")
    update_foreign_key("roulette", "user_id")
    with also_move_pkey("user_duel_stats", "user_id"):
        update_foreign_key("user_duel_stats", "user_id")

    # delete users that were not found. farewell...
    # the ON DELETE rules we set before will make these users disappear from other data structures too
    cursor.execute('DELETE FROM "user" WHERE twitch_id IS NULL')

    # drop the internal ID column
    cursor.execute('ALTER TABLE "user" DROP COLUMN id')

    # we can also now set the display name to be non-null
    # since we definitely eliminated any legacy rows that might be missing that value
    cursor.execute('ALTER TABLE "user" ALTER COLUMN name SET NOT NULL')

    # Rename the twitch_id to id, and make it primary key
    cursor.execute('ALTER TABLE "user" RENAME COLUMN twitch_id TO id')
    cursor.execute('ALTER TABLE "user" ALTER COLUMN id SET NOT NULL')
    cursor.execute('ALTER TABLE "user" ADD PRIMARY KEY(id)')

    def delete_foreign_key(table, column):
        cursor.execute(f"ALTER TABLE {table} DROP CONSTRAINT {table}_{column}_fkey")

    def add_foreign_key_again(table, column, nullable=False):
        if nullable:
            on_delete_action = "SET NULL"
        else:
            on_delete_action = "CASCADE"
        cursor.execute(
            f'ALTER TABLE {table} ADD FOREIGN KEY ({column}) REFERENCES "user"(id) ON DELETE {on_delete_action}'
        )

    # now this is special: We first had a users table with a primary key on the internal ID,
    # then added a UNIQUE INDEX on (twitch_id) so we could have foreign keys pointing
    # to the twitch_id (in update_foreign_key). We needed to definitely add those foreign keys back
    # so we can get the cascading effect from the DELETE FROM "user" statement.
    # Now we are left with two UNIQUE indexes indexing the same thing:
    # - "user_pkey" PRIMARY KEY, btree (id)
    # - "user_twitch_id_idx" UNIQUE, btree (id)
    # all those foreign keys we created earlier are all referring (depend) on user_twitch_id_idx.
    # If we want to eliminate user_twitch_id_idx, we have to drop all those foreign key constraints,
    # DROP the index, and then create them again to make them use the primary key index (as they should).
    # so this is what the following block does.
    delete_foreign_key("banphrase_data", "added_by")
    delete_foreign_key("banphrase_data", "edited_by")
    delete_foreign_key("command_data", "added_by")
    delete_foreign_key("command_data", "edited_by")
    delete_foreign_key("hsbet_bet", "user_id")
    delete_foreign_key("pleblist_song", "user_id")
    delete_foreign_key("prediction_run_entry", "user_id")
    delete_foreign_key("roulette", "user_id")
    delete_foreign_key("user_duel_stats", "user_id")

    cursor.execute("DROP INDEX user_twitch_id_idx")

    add_foreign_key_again("banphrase_data", "added_by", nullable=True)
    add_foreign_key_again("banphrase_data", "edited_by", nullable=True)
    add_foreign_key_again("command_data", "added_by", nullable=True)
    add_foreign_key_again("command_data", "edited_by", nullable=True)
    add_foreign_key_again("hsbet_bet", "user_id")
    add_foreign_key_again("pleblist_song", "user_id")
    add_foreign_key_again("prediction_run_entry", "user_id")
    add_foreign_key_again("roulette", "user_id")
    add_foreign_key_again("user_duel_stats", "user_id")

    # new: login_last_updated (+triggers)
    cursor.execute('ALTER TABLE "user" ADD COLUMN login_last_updated TIMESTAMPTZ NOT NULL DEFAULT now()')
    cursor.execute(
        """
    CREATE FUNCTION trigger_user_update_login_last_updated()
    RETURNS trigger AS
    $$
    BEGIN
        NEW.login_last_updated = now();
        RETURN NEW;
    END
    $$
    LANGUAGE plpgsql
    """
    )
    cursor.execute(
        """
    CREATE TRIGGER user_login_update
    AFTER UPDATE OF login ON "user"
    FOR EACH ROW EXECUTE PROCEDURE trigger_user_update_login_last_updated()
    """
    )

    with RedisManager.pipeline_context() as redis_pipeline:
        # Overwrite admin logs
        redis_pipeline.delete(admin_logs_key)
        if len(new_log_entries) > 0:
            redis_pipeline.rpush(admin_logs_key, *[json.dumps(entry) for entry in new_log_entries])

        # Delete data that was moved in
        redis_pipeline.delete(
            f"{bot.streamer}:users:num_lines",
            f"{bot.streamer}:users:tokens",
            f"{bot.streamer}:users:last_seen",
            f"{bot.streamer}:users:last_active",
            f"{bot.streamer}:users:username_raw",
            f"{bot.streamer}:users:ignored",
            f"{bot.streamer}:users:banned",
        )

    # at the end of this migration, we are left with this users table:
    # pajbot=# \d+ user
    #                                                        Table "pajbot1_streamer.user"
    #         Column        |           Type           | Collation | Nullable |       Default        | Storage  | Stats target | Description
    # ----------------------+--------------------------+-----------+----------+----------------------+----------+--------------+-------------
    #  login                | text                     |           | not null |                      | extended |              |
    #  name                 | text                     |           | not null |                      | extended |              |
    #  level                | integer                  |           | not null | 100                  | plain    |              |
    #  points               | bigint                   |           | not null | 0                    | plain    |              |
    #  subscriber           | boolean                  |           | not null | false                | plain    |              |
    #  time_in_chat_online  | interval                 |           | not null | '00:00:00'::interval | plain    |              |
    #  time_in_chat_offline | interval                 |           | not null | '00:00:00'::interval | plain    |              |
    #  id                   | text                     |           | not null |                      | extended |              |
    #  moderator            | boolean                  |           | not null | false                | plain    |              |
    #  num_lines            | bigint                   |           | not null | 0                    | plain    |              |
    #  tokens               | integer                  |           | not null | 0                    | plain    |              |
    #  last_seen            | timestamp with time zone |           |          |                      | plain    |              |
    #  last_active          | timestamp with time zone |           |          |                      | plain    |              |
    #  ignored              | boolean                  |           | not null | false                | plain    |              |
    #  banned               | boolean                  |           | not null | false                | plain    |              |
    #  login_last_updated   | timestamp with time zone |           | not null | now()                | plain    |              |
    # Indexes:
    #     "user_pkey" PRIMARY KEY, btree (id)
    #     "user_login_idx" UNIQUE, btree (login)
    #     "user_num_lines_idx" btree (num_lines)
    #     "user_points_idx" btree (points)
    # Referenced by:
    #     TABLE "banphrase_data" CONSTRAINT "banphrase_data_added_by_fkey" FOREIGN KEY (added_by) REFERENCES "user"(id) ON DELETE SET NULL
    #     TABLE "banphrase_data" CONSTRAINT "banphrase_data_edited_by_fkey" FOREIGN KEY (edited_by) REFERENCES "user"(id) ON DELETE SET NULL
    #     TABLE "command_data" CONSTRAINT "command_data_added_by_fkey" FOREIGN KEY (added_by) REFERENCES "user"(id) ON DELETE SET NULL
    #     TABLE "command_data" CONSTRAINT "command_data_edited_by_fkey" FOREIGN KEY (edited_by) REFERENCES "user"(id) ON DELETE SET NULL
    #     TABLE "hsbet_bet" CONSTRAINT "hsbet_bet_user_id_fkey" FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE
    #     TABLE "pleblist_song" CONSTRAINT "pleblist_song_user_id_fkey" FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE
    #     TABLE "prediction_run_entry" CONSTRAINT "prediction_run_entry_user_id_fkey" FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE
    #     TABLE "roulette" CONSTRAINT "roulette_user_id_fkey" FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE
    #     TABLE "user_duel_stats" CONSTRAINT "user_duel_stats_user_id_fkey" FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE
    # Triggers:
    #     user_login_update AFTER UPDATE OF login ON "user" FOR EACH ROW EXECUTE PROCEDURE trigger_user_update_login_last_updated()
