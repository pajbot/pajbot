#!/usr/bin/env python3

import functools
import sys
import os

import MySQLdb
import datetime

import logging
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values

# add /opt/pajbot (parent directory) to the PYTHONPATH
# so we can import from pajbot.migration, etc..
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import pajbot.migration_revisions.db  # noqa E402 module level import not at top of file
from pajbot.migration.db import DatabaseMigratable  # noqa E402 module level import not at top of file
from pajbot.migration.migrate import Migration  # noqa E402 module level import not at top of file

# python buffers full lines by default
# to make sure we see the progress as-it-is-created
# we make each call to print() use the flush=True parameter by default like this
print = functools.partial(print, flush=True)

print("MySQL: connecting... ", end="")
# https://pymysql.readthedocs.io/en/latest/modules/connections.html#pymysql.connections.Connection
mysql_conn = MySQLdb.connect(unix_socket="/var/run/mysqld/mysqld.sock", database="pajbot_streamer", charset="utf8mb4")
print("done.")

print("PostgreSQL: connecting... ", end="")
# http://initd.org/psycopg/docs/module.html#psycopg2.connect
# https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
psql_conn = psycopg2.connect("dbname=pajbot options='-c search_path=pajbot1_streamer'")
print("done.")


def tuple_replace(tpl, idx, converter):
    lst = list(tpl)
    if lst[idx] is not None:
        lst[idx] = converter(lst[idx])
    return tuple(lst)


def coerce(rows, idx, converter):
    return [tuple_replace(row, idx, converter) for row in rows]


def coerce_to_boolean(rows, idx):
    return coerce(rows, idx, bool)


def coerce_to_utc_time(rows, idx):
    def add_tz_field(dt):
        return dt.replace(tzinfo=datetime.timezone.utc)

    return coerce(rows, idx, add_tz_field)


logging.basicConfig(level=logging.DEBUG)

print("PostgreSQL: Creating schema... ", end="")
db_migratable = DatabaseMigratable(psql_conn)
db_migration = Migration(db_migratable, pajbot.migration_revisions.db)
# only run the initial migration (=up to ID 1),
# keeps this script compatible with future incompatible DB schema changes
db_migration.run(target_revision_id=1)
print("done.")


with mysql_conn.cursor() as mysql, psql_conn.cursor() as psql:

    def copy_table(destination_table_name, columns, coercions={}):
        source_table_name = "tb_" + destination_table_name

        print(f"Transfer table contents: {source_table_name}: Querying MySQL... ", end="")

        mysql.execute(f"SELECT {','.join(columns)} FROM {source_table_name}")
        rows = mysql.fetchall()

        print("Applying coercions in-memory... ", end="")

        for column_name, coercion in coercions.items():
            row_id = columns.index(column_name)
            rows = coercion(rows, row_id)

        rows = list(rows)

        print("Inserting into PostgreSQL... ", end="")

        # psql.execute(sql.SQL("DELETE FROM {}").format(sql.Identifier(destination_table_name)))
        psql_sql = sql.SQL("INSERT INTO {} VALUES %s").format(sql.Identifier(destination_table_name))
        execute_values(psql, psql_sql, rows)

        print("done.")

    def copy_auto_increment(destination_table_name, column_name):
        source_table_name = "tb_" + destination_table_name

        print(f"Transfer AUTO_INCREMENT: {source_table_name}.{column_name}: Querying MySQL... ", end="")

        mysql.execute(
            "SELECT `AUTO_INCREMENT` FROM INFORMATION_SCHEMA.TABLES WHERE "
            "TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s",
            (source_table_name,),
        )
        row = mysql.fetchone()
        if row is None:
            raise ValueError(f"error copying autoincrement for {source_table_name}: table not found")

        # mysql gives us the next value
        # in PostgreSQL, we have to set the current (last) value
        increment_value = row[0]

        print("Updating in PostgreSQL... ", end="")

        # pg_get_serial_sequence(): https://www.postgresql.org/docs/current/functions-info.html
        # Gets the sequence name associated with a table/column combination
        # (e.g. for "banphrase" and "id" returns "banphrase_id_seq")
        # setval(): https://www.postgresql.org/docs/current/functions-sequence.html
        # setval(<sequence name>, <value>, false) will set the sequence to return <value> on next call/usage
        # (That is what MySQL returns us - the value upon next invocation)
        psql.execute(
            "SELECT setval(pg_get_serial_sequence(%(table_name)s, %(column_name)s), %(increment_value)s, false)",
            {"table_name": destination_table_name, "column_name": column_name, "increment_value": increment_value},
        )

        print("done.")

    copy_table(
        "user",
        [
            "id",
            "username",
            "username_raw",
            "level",
            "points",
            "subscriber",
            "minutes_in_chat_online",
            "minutes_in_chat_offline",
        ],
        {"subscriber": coerce_to_boolean},
    )
    copy_auto_increment("user", "id")

    copy_table(
        "banphrase",
        [
            "id",
            "name",
            "phrase",
            "length",
            "permanent",
            "warning",
            "notify",
            "case_sensitive",
            "enabled",
            "operator",
            "sub_immunity",
            "remove_accents",
        ],
        {
            "permanent": coerce_to_boolean,
            "warning": coerce_to_boolean,
            "notify": coerce_to_boolean,
            "case_sensitive": coerce_to_boolean,
            "enabled": coerce_to_boolean,
            "sub_immunity": coerce_to_boolean,
            "remove_accents": coerce_to_boolean,
        },
    )
    copy_auto_increment("banphrase", "id")

    copy_table("banphrase_data", ["banphrase_id", "num_uses", "added_by", "edited_by"])

    copy_table(
        "command",
        [
            "id",
            "level",
            "action",
            "extra_args",
            "command",
            "description",
            "delay_all",
            "delay_user",
            "enabled",
            "cost",
            "can_execute_with_whisper",
            "sub_only",
            "mod_only",
            "tokens_cost",
            "run_through_banphrases",
        ],
        {
            "enabled": coerce_to_boolean,
            "can_execute_with_whisper": coerce_to_boolean,
            "sub_only": coerce_to_boolean,
            "mod_only": coerce_to_boolean,
            "run_through_banphrases": coerce_to_boolean,
        },
    )
    copy_auto_increment("command", "id")

    copy_table(
        "command_data",
        ["command_id", "num_uses", "added_by", "edited_by", "last_date_used"],
        {"last_date_used": coerce_to_utc_time},
    )

    copy_table("command_example", ["id", "command_id", "title", "chat", "description"])
    copy_auto_increment("command_example", "id")

    copy_table(
        "deck",
        ["id", "name", "class", "link", "first_used", "last_used", "times_used"],
        {"first_used": coerce_to_utc_time, "last_used": coerce_to_utc_time},
    )
    copy_auto_increment("deck", "id")

    copy_table("hsbet_game", ["id", "internal_id", "outcome"])
    copy_auto_increment("hsbet_game", "id")

    copy_table("hsbet_bet", ["id", "game_id", "user_id", "outcome", "points", "profit"])
    copy_auto_increment("hsbet_bet", "id")

    copy_table("link_blacklist", ["id", "domain", "path", "level"])
    copy_auto_increment("link_blacklist", "id")

    copy_table("link_whitelist", ["id", "domain", "path"])
    copy_auto_increment("link_whitelist", "id")

    copy_table(
        "link_data",
        ["id", "url", "times_linked", "first_linked", "last_linked"],
        {"first_linked": coerce_to_utc_time, "last_linked": coerce_to_utc_time},
    )
    copy_auto_increment("link_data", "id")

    copy_table("module", ["id", "enabled", "settings"], {"enabled": coerce_to_boolean})

    copy_table("playsound", ["name", "link", "volume", "cooldown", "enabled"], {"enabled": coerce_to_boolean})

    copy_table(
        "prediction_run",
        ["id", "winner_id", "started", "ended", "open", "type"],
        {"started": coerce_to_utc_time, "ended": coerce_to_utc_time, "open": coerce_to_boolean},
    )
    copy_auto_increment("prediction_run", "id")

    copy_table("prediction_run_entry", ["id", "prediction_run_id", "user_id", "prediction"])
    copy_auto_increment("prediction_run_entry", "id")

    copy_table("roulette", ["id", "user_id", "created_at", "points"], {"created_at": coerce_to_utc_time})
    copy_auto_increment("roulette", "id")

    copy_table(
        "stream",
        ["id", "title", "stream_start", "stream_end", "ended"],
        {"stream_start": coerce_to_utc_time, "stream_end": coerce_to_utc_time, "ended": coerce_to_boolean},
    )
    copy_auto_increment("stream", "id")

    copy_table(
        "stream_chunk",
        ["id", "stream_id", "broadcast_id", "video_url", "chunk_start", "chunk_end", "video_preview_image_url"],
        {"chunk_start": coerce_to_utc_time, "chunk_end": coerce_to_utc_time},
    )
    copy_auto_increment("stream_chunk", "id")

    copy_table(
        "timer",
        ["id", "name", "action", "interval_online", "interval_offline", "enabled"],
        {"enabled": coerce_to_boolean},
    )
    copy_auto_increment("timer", "id")

    copy_table("twitter_following", ["id", "username"])
    copy_auto_increment("twitter_following", "id")

    copy_table(
        "user_duel_stats",
        [
            "user_id",
            "duels_won",
            "duels_total",
            "points_won",
            "points_lost",
            "last_duel",
            "current_streak",
            "longest_losestreak",
            "longest_winstreak",
        ],
        {"last_duel": coerce_to_utc_time},
    )

    copy_table("web_content", ["id", "page", "content"])
    copy_auto_increment("web_content", "id")

print("mysql: rollback transaction... ", end="")
mysql_conn.rollback()
print("closing connection... ", end="")
mysql_conn.close()
print("done.")

print("PostgreSQL: commit transaction... ", end="")
psql_conn.commit()
print("closing connection... ", end="")
psql_conn.close()
print("done.")
