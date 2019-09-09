import logging

import json
from sqlalchemy import update

from pajbot.managers.db import DBManager
from pajbot.managers.redis import RedisManager
from pajbot.models.banphrase import BanphraseData
from pajbot.models.command import Command, CommandExample, CommandData
from pajbot.models.duel import UserDuelStats
from pajbot.models.hsbet import HSBetBet
from pajbot.models.pleblist import PleblistSong
from pajbot.models.roulette import Roulette
from pajbot.models.user import User, UserSQLCache, UserRedis
from pajbot.modules import BaseModule, BasicCommandsModule, ModuleType
from pajbot.modules.predict import PredictionRunEntry, PredictionRun
from pajbot.streamhelper import StreamHelper

log = logging.getLogger(__name__)


class NamechangeModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Name change"
    DESCRIPTION = "Transfer a user's data from their old twitch username to their new username"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED
    PARENT_MODULE = BasicCommandsModule

    def namechange_cmd(self, source, message, bot, **rest):
        # TODO refactor later that message is not None (bot.py:754)
        if message is None:
            message = ""

        message_split = message.split(" ")

        if len(message_split) < 2:
            bot.whisper(source.username, "Usage: !namechange oldusername newusername")
            return False

        old_username = message_split[0].lower()
        new_username = message_split[1].lower()

        # used later for redis, but we have to figure it out via SQL
        old_user_id = None
        new_user_id = None

        # DB Updates
        with DBManager.create_session_scope() as db_session:
            old_user = db_session.query(User).filter(User.username == old_username).one_or_none()
            new_user = db_session.query(User).filter(User.username == new_username).one_or_none()

            if old_user is None:
                bot.whisper(source.username, "User {} was not found".format(old_username))
                return False

            if new_user is None:
                bot.whisper(source.username, "User {} was not found".format(new_username))
                return False

            old_user_id = old_user.id
            new_user_id = new_user.id

            # we will migrate data created on the new user into the old user, and delete the new user
            # so the user will effectively "keep" their old ID
            db_session.delete(new_user)
            db_session.flush()

            old_user.level = max(old_user.level, new_user.level)
            old_user.points += new_user.points
            old_user.minutes_in_chat_online += new_user.minutes_in_chat_online
            old_user.minutes_in_chat_offline += new_user.minutes_in_chat_offline
            old_user.username = new_user.username
            old_user.username_raw = new_user.username_raw
            old_user.subscriber = new_user.subscriber

            old_duel_stats = db_session.query(UserDuelStats).filter_by(user_id=old_user.id).one_or_none()
            new_duel_stats = db_session.query(UserDuelStats).filter_by(user_id=new_user.id).one_or_none()

            # new user has duel stats, old user didn't.
            # so we can just move the new stats.
            if old_duel_stats is None and new_duel_stats is not None:
                new_duel_stats.user_id = old_user.id

            # new and old users have duel stats. merge them.
            if old_duel_stats is not None and new_duel_stats is not None:
                old_duel_stats.duels_won += new_duel_stats.duels_won
                old_duel_stats.duels_total += new_duel_stats.duels_total
                old_duel_stats.points_won += new_duel_stats.points_won
                old_duel_stats.points_lost += new_duel_stats.points_lost
                old_duel_stats.last_duel = new_duel_stats.last_duel

                if old_duel_stats.current_streak > 0 and new_duel_stats.current_streak >= 0:
                    # concat two winstreaks
                    old_duel_stats.current_streak += new_duel_stats.current_streak
                elif old_duel_stats.current_streak < 0 and new_duel_stats.current_streak <= 0:
                    # concat two losestreaks
                    old_duel_stats.current_streak -= new_duel_stats.current_streak
                else:
                    # streak has changed direction between old and new user, overwrite streak
                    old_duel_stats.current_streak = new_duel_stats.current_streak

                old_duel_stats.longest_winstreak = max(
                    old_duel_stats.longest_winstreak, new_duel_stats.longest_winstreak
                )
                old_duel_stats.longest_losestreak = max(
                    old_duel_stats.longest_losestreak, new_duel_stats.longest_losestreak
                )

                db_session.delete(new_duel_stats)
            # else: new user doesn't have duel stats, old user has. Nothing to move.

            db_session.execute(
                update(BanphraseData).where(BanphraseData.added_by == new_user.id).values(added_by=old_user.id)
            )
            db_session.execute(
                update(BanphraseData).where(BanphraseData.edited_by == new_user.id).values(edited_by=old_user.id)
            )
            db_session.execute(
                update(CommandData).where(CommandData.added_by == new_user.id).values(added_by=old_user.id)
            )
            db_session.execute(
                update(CommandData).where(CommandData.edited_by == new_user.id).values(edited_by=old_user.id)
            )
            db_session.execute(
                update(PredictionRun).where(PredictionRun.winner_id == new_user.id).values(winner_id=old_user.id)
            )
            db_session.execute(
                update(PredictionRunEntry).where(PredictionRunEntry.user_id == new_user.id).values(user_id=old_user.id)
            )
            db_session.execute(update(HSBetBet).where(HSBetBet.user_id == new_user.id).values(user_id=old_user.id))
            db_session.execute(
                update(PleblistSong).where(PleblistSong.user_id == new_user.id).values(user_id=old_user.id)
            )
            db_session.execute(
                update(PredictionRunEntry).where(PredictionRunEntry.user_id == new_user.id).values(user_id=old_user.id)
            )
            db_session.execute(update(Roulette).where(Roulette.user_id == new_user.id).values(user_id=old_user.id))

            db_session.commit()

        # reset cache for old and new users
        # .pop(key, None) deletes the mapping if it exists (del dict[key] raises KeyError if mapping is missing)
        bot.users.data.pop(new_username, None)
        bot.users.data.pop(old_username, None)
        UserSQLCache.cache.pop(new_username, None)
        UserSQLCache.cache.pop(old_username, None)

        redis = RedisManager.get()

        # num_lines, tokens
        for key in UserRedis.SS_KEYS:
            redis_key = "{streamer}:users:{key}".format(streamer=StreamHelper.get_streamer(), key=key)
            current_value = redis.zscore(redis_key, old_username)
            if current_value is not None:
                # TODO: The UserRedis implementation currently ZREMs the value
                #   if the value would be 0,
                #   this implementation here can/would create mappings with score = 0 too
                redis.zincrby(redis_key, current_value, new_username)

        # last_seen, last_active, username_raw, ignored, banned
        for key in UserRedis.HASH_KEYS:
            redis_key = "{streamer}:users:{key}".format(streamer=StreamHelper.get_streamer(), key=key)
            redis.hset(redis_key, new_username, redis.hget(redis_key, old_username))
            redis.hdel(redis_key, old_username)

        # banned, ignored
        for key in UserRedis.BOOL_KEYS:
            redis_key = "{streamer}:users:{key}".format(streamer=StreamHelper.get_streamer(), key=key)
            old_val = redis.hget(redis_key, old_username) is not None
            new_val = redis.hget(redis_key, new_username) is not None
            combined_val = old_val or new_val

            if combined_val:
                redis.hset(redis_key, new_username, 1)
            else:
                redis.hdel(redis_key, new_username)

            redis.hdel(redis_key, old_username)

        # admin logs
        admin_logs_key = "{streamer}:logs:admin".format(streamer=StreamHelper.get_streamer())
        all_admin_logs = redis.lrange(admin_logs_key, 0, -1)
        for idx, raw_log_entry in enumerate(all_admin_logs):
            log_entry = json.loads(raw_log_entry)
            if log_entry["user_id"] == new_user_id:
                log_entry["user_id"] = old_user_id
                redis.lset(admin_logs_key, idx, json.dumps(log_entry))

        # personal uptime
        # all_personal_uptimes maps a string stream ID (e.g. "115") to a string json blob mapping username to
        # minutes the user spent watching that stream
        personal_uptimes_redis_key = "{streamer}:viewer_data".format(streamer=StreamHelper.get_streamer())
        all_personal_uptimes = redis.hgetall(personal_uptimes_redis_key)
        for stream_id, raw_personal_uptimes in all_personal_uptimes.items():
            personal_uptimes = json.loads(raw_personal_uptimes)
            if new_username not in personal_uptimes:
                continue  # no need to update this stream's viewer data

            personal_uptimes[old_username] = personal_uptimes.get(old_username, 0) + personal_uptimes[new_username]
            del personal_uptimes[new_username]
            redis.hset(personal_uptimes_redis_key, stream_id, json.dumps(personal_uptimes))

        bot.whisper(source.username, "Successfully migrated all data from {} to {}".format(old_username, new_username))

    def load_commands(self, **options):
        self.commands["namechange"] = Command.raw_command(
            self.namechange_cmd,
            level=2000,
            description="Transfer a user's data from their old twitch username to their new username",
            examples=[
                CommandExample(
                    None,
                    "Transfer data from forsenlol to forsen",
                    chat="user:!namechange forsenlol forsen\n"
                    "bot: Successfully transferred stats from forsenlol to forsen.",
                ).parse()
            ],
        )
