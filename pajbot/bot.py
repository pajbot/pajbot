from typing import Any, List, Callable

import cgi
import datetime
import logging
import re
import sys
import urllib

import irc.client
import random
import requests
import threading
from pytz import timezone

import pajbot.migration_revisions.db
import pajbot.migration_revisions.redis
from pajbot.action_queue import ActionQueue
from pajbot.apiwrappers.authentication.access_token import UserAccessToken
from pajbot.apiwrappers.authentication.client_credentials import ClientCredentials
from pajbot.apiwrappers.authentication.token_manager import AppAccessTokenManager, UserAccessTokenManager
from pajbot.apiwrappers.twitch.helix import TwitchHelixAPI
from pajbot.apiwrappers.twitch.id import TwitchIDAPI
from pajbot.apiwrappers.twitch.tmi import TwitchTMIAPI
from pajbot.constants import VERSION
from pajbot.eventloop import SafeDefaultScheduler
from pajbot.managers.command import CommandManager
from pajbot.managers.db import DBManager
from pajbot.managers.deck import DeckManager
from pajbot.managers.emote import EmoteManager, EpmManager, EcountManager
from pajbot.managers.handler import HandlerManager
from pajbot.managers.irc import IRCManager
from pajbot.managers.kvi import KVIManager
from pajbot.managers.redis import RedisManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.managers.twitter import TwitterManager, PBTwitterManager
from pajbot.managers.user_ranks_refresh import UserRanksRefreshManager
from pajbot.managers.websocket import WebSocketManager
from pajbot.migration.db import DatabaseMigratable
from pajbot.migration.migrate import Migration
from pajbot.migration.redis import RedisMigratable
from pajbot.models.action import ActionParser, SubstitutionFilter
from pajbot.models.banphrase import BanphraseManager
from pajbot.models.moderation_action import Ban, Timeout, Unban, Untimeout, new_message_processing_scope
from pajbot.models.module import ModuleManager
from pajbot.models.pleblist import PleblistManager
from pajbot.models.sock import SocketManager
from pajbot.models.stream import StreamManager
from pajbot.models.timer import TimerManager
from pajbot.models.user import User, UserBasics
from pajbot.streamhelper import StreamHelper
from pajbot.tmi import TMIRateLimits, WhisperOutputMode
from pajbot import utils

log = logging.getLogger(__name__)

SLICE_REGEX = re.compile(r"(-?\d+)?(:?(-?\d+)?)?")


class Bot:
    """
    Main class for the twitch bot
    """

    def __init__(self, config, args):
        self.config = config
        self.args = args

        ScheduleManager.init()

        DBManager.init(self.config["main"]["db"])

        # redis
        redis_options = {}
        if "redis" in config:
            redis_options = dict(config.items("redis"))
        RedisManager.init(**redis_options)
        utils.wait_for_redis_data_loaded(RedisManager.get())

        self.nickname = config["main"].get("nickname", "pajbot")

        if config["main"].getboolean("verified", False):
            self.tmi_rate_limits = TMIRateLimits.VERIFIED
        elif config["main"].getboolean("known", False):
            self.tmi_rate_limits = TMIRateLimits.KNOWN
        else:
            self.tmi_rate_limits = TMIRateLimits.BASE

        self.whisper_output_mode = WhisperOutputMode.from_config_value(
            config["main"].get("whisper_output_mode", "normal")
        )

        # phrases
        self.phrases = {
            "welcome": ["{nickname} {version} running! HeyGuys"],
            "quit": ["{nickname} {version} shutting down... BibleThump"],
        }
        if "phrases" in config:
            phrases = config["phrases"]
            if "welcome" in phrases:
                self.phrases["welcome"] = phrases["welcome"].splitlines()
            if "quit" in phrases:
                self.phrases["quit"] = phrases["quit"].splitlines()
        # Remembers whether the "welcome" phrases have already been said. We don't want to send the
        # welcome messages to chat again on a reconnect.
        self.welcome_messages_sent = False

        # streamer
        if "streamer" in config["main"]:
            self.streamer: str = config["main"]["streamer"]
            self.channel = "#" + self.streamer
        elif "target" in config["main"]:
            self.channel = config["main"]["target"]
            self.streamer: str = self.channel[1:]

        self.bot_domain = self.config["web"]["domain"]
        self.streamer_display = self.config["web"]["streamer_name"]

        log.debug("Loaded config")

        # do this earlier since schema upgrade can depend on the helix api
        self.api_client_credentials = ClientCredentials(
            self.config["twitchapi"]["client_id"],
            self.config["twitchapi"]["client_secret"],
            self.config["twitchapi"]["redirect_uri"],
        )

        self.twitch_id_api = TwitchIDAPI(self.api_client_credentials)
        self.twitch_tmi_api = TwitchTMIAPI()
        self.app_token_manager = AppAccessTokenManager(self.twitch_id_api, RedisManager.get())
        self.twitch_helix_api: TwitchHelixAPI = TwitchHelixAPI(RedisManager.get(), self.app_token_manager)

        self.bot_user_id = self.twitch_helix_api.get_user_id(self.nickname)
        if self.bot_user_id is None:
            raise ValueError("The bot login name you entered under [main] does not exist on twitch.")

        self.broadcaster = self.twitch_helix_api.get_user_basics_by_login(self.streamer)
        if self.broadcaster is None:
            raise ValueError("The streamer login name you entered under [main] does not exist on twitch.")

        self.streamer_user_id = self.broadcaster.id

        self.streamer_access_token_manager = UserAccessTokenManager(
            api=self.twitch_id_api, redis=RedisManager.get(), username=self.streamer, user_id=self.streamer_user_id
        )

        StreamHelper.init_streamer(self.streamer, self.streamer_user_id, self.streamer_display)

        # SQL migrations
        with DBManager.create_dbapi_connection_scope() as sql_conn:
            sql_migratable = DatabaseMigratable(sql_conn)
            sql_migration = Migration(sql_migratable, pajbot.migration_revisions.db, self)
            sql_migration.run()

        # Redis migrations
        redis_migratable = RedisMigratable(redis_options=redis_options, namespace=self.streamer)
        redis_migration = Migration(redis_migratable, pajbot.migration_revisions.redis, self)
        redis_migration.run()

        # Thread pool executor for async actions
        self.action_queue = ActionQueue()

        # refresh points_rank and num_lines_rank regularly
        UserRanksRefreshManager.start(self.action_queue)

        self.reactor = irc.client.Reactor()
        # SafeDefaultScheduler makes the bot not exit on exception in the main thread
        # e.g. on actions via bot.execute_now, etc.
        self.reactor.scheduler_class = SafeDefaultScheduler
        self.reactor.scheduler = SafeDefaultScheduler()

        self.start_time = utils.now()
        ActionParser.bot = self

        HandlerManager.init_handlers()

        self.socket_manager = SocketManager(self.streamer, self.execute_now)
        self.stream_manager = StreamManager(self)
        StreamHelper.init_stream_manager(self.stream_manager)

        self.decks = DeckManager()
        self.banphrase_manager = BanphraseManager(self).load()
        self.timer_manager = TimerManager(self).load()
        self.kvi = KVIManager()

        # bot access token
        if "password" in self.config["main"]:
            log.warning(
                "DEPRECATED - Using bot password/oauth token from file. "
                "You should authenticate in web gui using route /bot_login "
                "and remove password from config file"
            )

            access_token = self.config["main"]["password"]

            if access_token.startswith("oauth:"):
                access_token = access_token[6:]

            self.bot_token_manager = UserAccessTokenManager(
                api=None,
                redis=None,
                username=self.nickname,
                user_id=self.bot_user_id,
                token=UserAccessToken.from_implicit_auth_flow_token(access_token),
            )
        else:
            self.bot_token_manager = UserAccessTokenManager(
                api=self.twitch_id_api, redis=RedisManager.get(), username=self.nickname, user_id=self.bot_user_id
            )

        self.emote_manager = EmoteManager(self.twitch_helix_api, self.action_queue)
        self.epm_manager = EpmManager()
        self.ecount_manager = EcountManager()
        if "twitter" in self.config and self.config["twitter"].get("streaming_type", "twitter") == "tweet-provider":
            self.twitter_manager = PBTwitterManager(self)
        else:
            self.twitter_manager = TwitterManager(self)
        self.module_manager = ModuleManager(self.socket_manager, bot=self).load()
        self.commands = CommandManager(
            socket_manager=self.socket_manager, module_manager=self.module_manager, bot=self
        ).load()
        self.websocket_manager = WebSocketManager(self)

        HandlerManager.trigger("on_managers_loaded")

        # Commitable managers
        self.commitable = {"commands": self.commands, "banphrases": self.banphrase_manager}

        self.execute_every(60, self.commit_all)
        self.execute_every(1, self.do_tick)

        # promote the admin to level 2000
        self.admin = self.config["main"].get("admin", None)
        if self.admin is None:
            log.warning("No admin user specified. See the [main] section in the example config for its usage.")
        else:
            with DBManager.create_session_scope() as db_session:
                admin_user = User.find_or_create_from_login(db_session, self.twitch_helix_api, self.admin)
                if admin_user is None:
                    log.warning(
                        "The login name you entered for the admin user does not exist on twitch. "
                        "No admin user has been created."
                    )
                else:
                    admin_user.level = 2000

        # silent mode
        self.silent = (
            "flags" in config and "silent" in config["flags"] and config["flags"]["silent"] == "1"
        ) or args.silent
        if self.silent:
            log.info("Silent mode enabled")

        # dev mode
        self.dev = "flags" in config and "dev" in config["flags"] and config["flags"]["dev"] == "1"
        if self.dev:
            self.version_long = utils.extend_version_if_possible(VERSION)
        else:
            self.version_long = VERSION

        self.irc = IRCManager(self)

        relay_host = self.config["main"].get("relay_host", None)
        relay_password = self.config["main"].get("relay_password", None)
        if relay_host is not None or relay_password is not None:
            log.warning(
                "DEPRECATED - Relaybroker support is no longer implemented. relay_host and relay_password are ignored"
            )

        self.data = {
            "broadcaster": self.streamer,
            "version": self.version_long,
            "version_brief": VERSION,
            "bot_name": self.nickname,
            "bot_domain": self.bot_domain,
            "streamer_display": self.streamer_display,
        }

        self.data_cb = {
            "status_length": self.c_status_length,
            "stream_status": self.c_stream_status,
            "bot_uptime": self.c_uptime,
            "current_time": self.c_current_time,
            "molly_age_in_years": self.c_molly_age_in_years,
        }

        self.user_agent = f"pajbot1/{VERSION} ({self.nickname})"

        self.thread_locals = threading.local()

        self.subs_only = False

    @property
    def password(self):
        return f"oauth:{self.bot_token_manager.token.access_token}"

    def start(self):
        """Start the IRC client."""
        self.reactor.process_forever()

    def get_kvi_value(self, key, extra={}):
        return self.kvi[key].get()

    def get_last_tweet(self, key, extra={}):
        return self.twitter_manager.get_last_tweet(key)

    def get_emote_epm(self, key, extra={}):
        epm = self.epm_manager.get_emote_epm(key)

        # maybe we simply haven't seen this emote yet (during the bot runtime) but it's a valid emote?
        if epm is None and self.emote_manager.match_word_to_emote(key) is not None:
            epm = 0

        if epm is None:
            return None

        # formats the number with grouping (e.g. 112,556) and zero decimal places
        return f"{epm:,.0f}"

    def get_emote_epm_record(self, key, extra={}):
        val = self.epm_manager.get_emote_epm_record(key)
        if val is None:
            return None
        # formats the number with grouping (e.g. 112,556) and zero decimal places
        return f"{val:,.0f}"

    def get_emote_count(self, key, extra={}):
        val = self.ecount_manager.get_emote_count(key)
        if val is None:
            return None
        # formats the number with grouping (e.g. 112,556) and zero decimal places
        return f"{val:,.0f}"

    @staticmethod
    def get_source_value(key, extra={}):
        try:
            return getattr(extra["source"], key)
        except:
            log.exception("Caught exception in get_source_value")

        return None

    def get_user_value(self, key, extra={}):
        try:
            with DBManager.create_session_scope() as db_session:
                user = User.find_by_user_input(db_session, extra["argument"])
                if user is not None:
                    return getattr(user, key)
        except:
            log.exception("Caught exception in get_source_value")

        return None

    @staticmethod
    def get_command_value(key, extra={}):
        try:
            return getattr(extra["command"].data, key)
        except:
            log.exception("Caught exception in get_source_value")

        return None

    def get_broadcaster_value(self, key, extra={}):
        try:
            return getattr(self.broadcaster, key)
        except:
            log.exception("Caught exception in get_broadcaster_value")

        return None

    def get_usersource_value(self, key, extra={}):
        try:
            with DBManager.create_session_scope() as db_session:
                user = User.find_by_user_input(db_session, extra["argument"])
                if user is not None:
                    return getattr(user, key)

            return getattr(extra["source"], key)
        except:
            log.exception("Caught exception in get_source_value")

        return None

    def get_time_value(self, key, extra={}):
        try:
            tz = timezone(key)
            return datetime.datetime.now(tz).strftime("%H:%M")
        except:
            log.exception("Unhandled exception in get_time_value")

        return None

    def get_date_value(self, key, extra={}):
        try:
            tz = timezone(key)
            return datetime.datetime.now(tz).strftime("%Y-%m-%d")
        except:
            log.exception("Unhandled exception in get_date_value")

    def get_datetimefromisoformat_value(self, key, extra={}):
        try:
            dt = datetime.datetime.fromisoformat(key)
            if dt.tzinfo is None:
                # The date format passed through in key did not contain a timezone, so we replace it with UTC
                dt = dt.replace(tzinfo=datetime.timezone.utc)

            return dt
        except:
            log.exception("Unhandled exception in get_datetimefromisoformat_value")

    def get_current_song_value(self, key, extra={}):
        if self.stream_manager.online:
            current_song = PleblistManager.get_current_song(self.stream_manager.current_stream.id)
            inner_keys = key.split(".")
            val = current_song
            for inner_key in inner_keys:
                val = getattr(val, inner_key, None)
                if val is None:
                    return None
            if val is not None:
                return val
        return None

    def get_strictargs_value(self, key, extra={}):
        ret = self.get_args_value(key, extra)

        if not ret:
            return None

        return ret

    @staticmethod
    def get_args_value(key, extra={}):
        r = None
        try:
            msg_parts = extra["message"].split(" ")
        except (KeyError, AttributeError):
            msg_parts = [""]

        try:
            if "-" in key:
                range_str = key.split("-")
                if len(range_str) == 2:
                    r = (int(range_str[0]), int(range_str[1]))

            if r is None:
                r = (int(key), len(msg_parts))
        except (TypeError, ValueError):
            r = (0, len(msg_parts))

        try:
            return " ".join(msg_parts[r[0] : r[1]])
        except AttributeError:
            return ""
        except:
            log.exception("UNHANDLED ERROR IN get_args_value")
            return ""

    def get_value(self, key, extra={}):
        if key in extra:
            return extra[key]

        if key in self.data:
            return self.data[key]

        if key in self.data_cb:
            return self.data_cb[key]()

        log.warning("Unknown key passed to get_value: %s", key)
        return None

    def privmsg_arr(self, arr, target=None):
        for msg in arr:
            self.privmsg(msg, target)

    def privmsg_arr_chunked(self, arr, per_chunk=35, chunk_delay=30, target=None):
        i = 0
        while arr:
            if i == 0:
                self.privmsg_arr(arr[:per_chunk], target)
            else:
                self.execute_delayed(chunk_delay * i, self.privmsg_arr, arr[:per_chunk], target)

            del arr[:per_chunk]

            i = i + 1

    def privmsg_from_file(self, url, per_chunk=35, chunk_delay=30, target=None):
        try:
            r = requests.get(url, headers={"User-Agent": self.user_agent})
            r.raise_for_status()

            content_type = r.headers["Content-Type"]
            if content_type is not None and cgi.parse_header(content_type)[0] != "text/plain":
                log.error("privmsg_from_file should be fed with a text/plain URL. Refusing to send.")
                return

            lines = r.text.splitlines()
            self.privmsg_arr_chunked(lines, per_chunk=per_chunk, chunk_delay=chunk_delay, target=target)
        except:
            log.exception("error in privmsg_from_file")

    # event is an event to clone and change the text from.
    # Usage: !eval bot.eval_from_file(event, 'https://pastebin.com/raw/LhCt8FLh')
    def eval_from_file(self, event, url):
        try:
            r = requests.get(url, headers={"User-Agent": self.user_agent})
            r.raise_for_status()

            content_type = r.headers["Content-Type"]
            if content_type is not None and cgi.parse_header(content_type)[0] != "text/plain":
                log.error("eval_from_file should be fed with a text/plain URL. Refusing to send.")
                return

            lines = r.text.splitlines()
            import copy

            for msg in lines:
                cloned_event = copy.deepcopy(event)
                cloned_event.arguments = [msg]
                # omit the source connection as None (since its not used)
                self.on_pubmsg(None, cloned_event)
            self.whisper_login(event.source.user.lower(), f"Successfully evaluated {len(lines)} lines")
        except:
            log.exception("BabyRage")
            self.whisper_login(event.source.user.lower(), "Exception BabyRage")

    def privmsg(self, message, channel=None):
        if channel is None:
            channel = self.channel

        self.irc.privmsg(channel, message, is_whisper=False)

    def c_uptime(self):
        return utils.time_ago(self.start_time)

    @staticmethod
    def c_current_time():
        return utils.now()

    @staticmethod
    def c_molly_age_in_years():
        molly_birth = datetime.datetime(2018, 10, 29, tzinfo=datetime.timezone.utc)
        now = utils.now()
        diff = now - molly_birth
        return diff.total_seconds() / 3600 / 24 / 365

    def get_datetime_value(self, key, extra=[]):
        try:
            tz = timezone(key)
            return datetime.datetime.now(tz)
        except:
            log.exception("Unhandled exception in get_datetime_value")

        return None

    @property
    def is_online(self):
        return self.stream_manager.online

    def c_stream_status(self):
        return "online" if self.stream_manager.online else "offline"

    def c_status_length(self):
        if self.stream_manager.online:
            return utils.time_ago(self.stream_manager.current_stream.stream_start)

        if self.stream_manager.last_stream is not None:
            return utils.time_ago(self.stream_manager.last_stream.stream_end)

        return "No recorded stream FeelsBadMan "

    def execute_now(self, function, *args, **kwargs):
        self.execute_delayed(0, function, *args, **kwargs)

    def execute_at(self, at, function, *args, **kwargs):
        self.reactor.scheduler.execute_at(at, lambda: function(*args, **kwargs))

    def execute_delayed(self, delay, function, *args, **kwargs):
        self.reactor.scheduler.execute_after(delay, lambda: function(*args, **kwargs))

    def execute_every(self, period, function, *args, **kwargs):
        self.reactor.scheduler.execute_every(period, lambda: function(*args, **kwargs))

    def _ban(self, login, reason=None):
        message = f"/ban {login}"
        if reason is not None:
            message += f" {reason}"
        self.privmsg(message)

    def ban(self, user, reason=None):
        self.ban_login(user.login, reason)

    def ban_login(self, login: str, reason=None):
        if self.thread_locals.moderation_actions is not None:
            self.thread_locals.moderation_actions.add(login, Ban(reason))
        else:
            self.timeout_login(login, 30, reason, once=True)
            self.execute_delayed(1, self._ban, login, reason)

    def unban(self, user):
        self.unban_login(user.login)

    def unban_login(self, login: str):
        if self.thread_locals.moderation_actions is not None:
            self.thread_locals.moderation_actions.add(login, Unban())
        else:
            self.privmsg(f"/unban {login}")

    def untimeout(self, user):
        self.untimeout_login(user.login)

    def untimeout_login(self, login: str):
        if self.thread_locals.moderation_actions is not None:
            self.thread_locals.moderation_actions.add(login, Untimeout())
        else:
            self.privmsg(f"/untimeout {login}")

    def _timeout(self, login: str, duration: int, reason=None):
        message = f"/timeout {login} {duration}"
        if reason is not None:
            message += f" {reason}"
        self.privmsg(message)

    def timeout(self, user, duration, reason=None, once=False):
        self.timeout_login(user.login, duration, reason, once)

    def timeout_login(self, login: str, duration: int, reason=None, once=False):
        if self.thread_locals.moderation_actions is not None:
            self.thread_locals.moderation_actions.add(login, Timeout(duration, reason, once))
        else:
            self._timeout(login, duration, reason)
            if not once:
                self.execute_delayed(1, self._timeout, login, duration, reason)

    def timeout_warn(self, user, duration: int, reason=None, once=False):
        duration, punishment = user.timeout(duration, warning_module=self.module_manager["warning"])
        self.timeout(user, duration, reason, once)
        return (duration, punishment)

    def delete_message(self, msg_id):
        self.privmsg(f"/delete {msg_id}")

    def whisper(self, user, message):
        if self.whisper_output_mode == WhisperOutputMode.NORMAL:
            self.irc.whisper(user.login, message)
        if self.whisper_output_mode == WhisperOutputMode.CHAT:
            self.privmsg(f"{user}, {message}")
        if self.whisper_output_mode == WhisperOutputMode.CONTROL:
            chub = self.config["main"].get("control_hub", None)
            if chub is not None:
                chub = f"#{chub}"
            self.privmsg(f"{user}, {message}", chub)
        elif self.whisper_output_mode == WhisperOutputMode.DISABLED:
            log.debug(f'Whisper "{message}" to user "{user}" was not sent (due to config setting)')

    def whisper_login(self, login, message):
        if self.whisper_output_mode == WhisperOutputMode.NORMAL:
            self.irc.whisper(login, message)
        if self.whisper_output_mode == WhisperOutputMode.CHAT:
            self.privmsg(f"{login}, {message}")
        if self.whisper_output_mode == WhisperOutputMode.CONTROL:
            chub = self.config["main"].get("control_hub", None)
            if chub is not None:
                chub = f"#{chub}"
            self.privmsg(f"{login}, {message}", chub)
        elif self.whisper_output_mode == WhisperOutputMode.DISABLED:
            log.debug(f'Whisper "{message}" to user "{login}" was not sent (due to config setting)')

    def send_message_to_user(self, user, message, event, method="say"):
        if method == "say":
            self.say(f"@{user.name}, {message}")
        elif method == "whisper":
            self.whisper(user, message)
        elif method == "me":
            self.me(message)
        elif method == "reply":
            if event.type in ["action", "pubmsg"]:
                msg_id = next(tag["value"] for tag in event.tags if tag["key"] == "id")
                self.reply(msg_id, message)
            elif event.type == "whisper":
                self.whisper(user, message)
        else:
            log.warning("Unknown send_message method: %s", method)

    def reply(self, msg_id, message, channel=None):
        if self.silent:
            return

        if not message:
            log.warning("message=None passed to Bot::reply()")
            return

        if not channel:
            channel = self.channel

        message = utils.clean_up_message(message)
        message = f"@reply-parent-msg-id={msg_id} PRIVMSG {channel} :{message}"

        self.irc.send_raw(message[:510])

    def say(self, message, channel=None):
        if message is None:
            log.warning("message=None passed to Bot::say()")
            return

        if self.silent:
            return

        message = utils.clean_up_message(message)
        self.privmsg(message[:510], channel)

    def is_bad_message(self, message):
        # Checks for banphrases
        return self.banphrase_manager.check_message(message, None) is not False

    def safe_privmsg(self, message, channel=None):
        if not self.is_bad_message(message):
            self.privmsg(message, channel)

    def safe_me(self, message, channel=None):
        if not self.is_bad_message(message):
            self.me(message, channel)

    def safe_say(self, message, channel=None):
        if not self.is_bad_message(message):
            self.say(message, channel)

    def me(self, message, channel=None):
        self.say("/me " + message[:500], channel=channel)

    def connect(self):
        self.irc.start()

    def parse_message(self, message, source, event, tags={}, whisper=False):
        msg_lower = message.lower()

        emote_tag = tags["emotes"]
        msg_id = tags.get("id", None)  # None on whispers!
        badges_string = tags.get("badges", "")
        badges = dict((badge.split("/") for badge in badges_string.split(",") if badge != ""))

        if not whisper and event.target == self.channel:
            # Moderator or broadcaster, both count
            source.moderator = tags["mod"] == "1" or source.id == self.streamer_user_id
            # Having the founder badge means that the subscriber tag is set to 0. Therefore it's more stable to just check badges
            source.subscriber = "founder" in badges or "subscriber" in badges
            # once they are a founder they are always be a founder, regardless if they are a sub or not.
            if not source.founder:
                source.founder = "founder" in badges
            source.vip = "vip" in badges

        if not whisper and source.banned:
            self.ban(
                source,
                reason=f"User is on the {self.nickname} banlist. Contact a moderator level 1000 or higher for unban.",
            )
            return False

        # Parse emotes in the message
        emote_instances, emote_counts = self.emote_manager.parse_all_emotes(message, emote_tag)

        now = utils.now()
        source.last_seen = now
        source.last_active = now

        if not whisper:
            # increment epm and ecount
            self.epm_manager.handle_emotes(emote_counts)
            self.ecount_manager.handle_emotes(emote_counts)

        urls = self.find_unique_urls(message)

        res = HandlerManager.trigger(
            "on_message",
            source=source,
            message=message,
            emote_instances=emote_instances,
            emote_counts=emote_counts,
            whisper=whisper,
            urls=urls,
            msg_id=msg_id,
            event=event,
        )
        if res is False:
            return False

        if source.ignored:
            return False

        if msg_lower[:1] == "!":
            msg_lower_parts = msg_lower.split(" ")
            trigger = msg_lower_parts[0][1:]
            msg_raw_parts = message.split(" ")
            remaining_message = " ".join(msg_raw_parts[1:]) if len(msg_raw_parts) > 1 else None
            if trigger in self.commands:
                command = self.commands[trigger]
                extra_args = {
                    "emote_instances": emote_instances,
                    "emote_counts": emote_counts,
                    "trigger": trigger,
                    "msg_id": msg_id,
                }
                command.run(self, source, remaining_message, event=event, args=extra_args, whisper=whisper)

    def on_whisper(self, chatconn, event):
        tags = {tag["key"]: tag["value"] if tag["value"] is not None else "" for tag in event.tags}

        id = tags["user-id"]
        login = event.source.user
        name = tags["display-name"]

        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            source = User.from_basics(db_session, UserBasics(id, login, name))
            self.parse_message(event.arguments[0], source, event, tags, whisper=True)

    def on_usernotice(self, chatconn, event):
        tags = {tag["key"]: tag["value"] if tag["value"] is not None else "" for tag in event.tags}

        if event.target != self.channel:
            return

        id = tags["user-id"]
        login = tags["login"]
        name = tags["display-name"]

        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            source = User.from_basics(db_session, UserBasics(id, login, name))
            if event.arguments and len(event.arguments) > 0:
                msg = event.arguments[0]
            else:
                msg = None  # e.g. user didn't type an extra message to share with the streamer

            with new_message_processing_scope(self):
                HandlerManager.trigger("on_usernotice", source=source, message=msg, tags=tags)

                if msg is not None:
                    self.parse_message(msg, source, event, tags)

    def on_action(self, chatconn, event):
        self.on_pubmsg(chatconn, event)

    def on_pubmsg(self, chatconn, event):
        tags = {tag["key"]: tag["value"] if tag["value"] is not None else "" for tag in event.tags}

        id = tags["user-id"]
        login = event.source.user
        name = tags["display-name"]

        if event.source.user == self.nickname:
            return False

        if self.streamer == "forsen":
            if "zonothene" in login:
                self._ban(login)
                return True

            raw_m = event.arguments[0].lower()
            if raw_m.startswith("!lastseen forsen"):
                if len(raw_m) > len("!lastseen forsen2"):
                    if raw_m[16] == " ":
                        return True
                else:
                    return True

            if raw_m.startswith("!lastseen @forsen"):
                if len(raw_m) > len("!lastseen @forsen2"):
                    if raw_m[17] == " ":
                        return True
                else:
                    return True

        if self.streamer == "nymn":
            if "hades_k" in login:
                self.timeout_login(login, 3600, reason="Bad username")
                return True

            if "hades_b" in login:
                self.timeout_login(login, 3600, reason="Bad username")
                return True

        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            source = User.from_basics(db_session, UserBasics(id, login, name))

            with new_message_processing_scope(self):
                res = HandlerManager.trigger("on_pubmsg", source=source, message=event.arguments[0], tags=tags)
                if res is False:
                    return False

                self.parse_message(event.arguments[0], source, event, tags=tags)

    def on_pubnotice(self, chatconn, event):
        tags = {tag["key"]: tag["value"] if tag["value"] is not None else "" for tag in event.tags}
        HandlerManager.trigger(
            "on_pubnotice",
            stop_on_false=False,
            channel=event.target[1:],
            msg_id=tags["msg-id"],
            message=event.arguments[0],
        )

    def on_clearchat(self, chatconn, event):
        tags = {tag["key"]: tag["value"] if tag["value"] is not None else "" for tag in event.tags}

        # Ignore "Chat has been cleared by a moderator" messages
        if "target-user-id" not in tags:
            return

        target_user_id = tags["target-user-id"]
        with DBManager.create_session_scope() as db_session:
            user = User.find_by_id(db_session, target_user_id)

            if user is None:
                # User is not otherwise known, we won't store their timeout (they need to type first)
                # We could theoretically also do an API call here to figure out everything about that user,
                # but that could easily overwhelm the bot when lots of unknown users are banned quickly (e.g. bots).
                return

            if "ban-duration" in tags:
                # timeout
                ban_duration = int(tags["ban-duration"])
                user.timeout_end = utils.now() + datetime.timedelta(seconds=ban_duration)
            else:
                # permaban
                # this sets timeout_end to None
                user.timed_out = False

    def on_welcome(self, _conn, _event):
        """Gets triggered on IRC welcome, i.e. when the login is successful."""
        if self.welcome_messages_sent:
            return

        for p in self.phrases["welcome"]:
            self.privmsg(p.format(nickname=self.nickname, version=self.version_long))

        self.welcome_messages_sent = True

    def on_roomstate(self, chatconn, event):
        tags = {tag["key"]: tag["value"] if tag["value"] is not None else "" for tag in event.tags}

        if event.target != self.channel:
            return

        if "subs-only" in tags:
            self.subs_only = tags["subs-only"] == "1"

    def commit_all(self):
        for key, manager in self.commitable.items():
            manager.commit()

        HandlerManager.trigger("on_commit", stop_on_false=False)

    @staticmethod
    def do_tick():
        HandlerManager.trigger("on_tick")

    def quit(self, message, event, **options):
        quit_chub = self.config["main"].get("control_hub", None)
        quit_delay = 0

        if quit_chub is not None and event.target == f"#{quit_chub}":
            quit_delay_random = 300
            try:
                if message is not None and int(message.split()[0]) >= 1:
                    quit_delay_random = int(message.split()[0])
            except (IndexError, ValueError, TypeError):
                pass
            quit_delay = random.randint(0, quit_delay_random)
            log.info("%s is restarting in %d seconds.", self.nickname, quit_delay)

        self.execute_delayed(quit_delay, self.quit_bot)

    def quit_bot(self, **options):
        self.commit_all()
        HandlerManager.trigger("on_quit")
        phrase_data = {"nickname": self.nickname, "version": self.version_long}

        try:
            ScheduleManager.base_scheduler.print_jobs()
            ScheduleManager.base_scheduler.shutdown(wait=False)
        except:
            log.exception("Error while shutting down the apscheduler")

        try:
            for p in self.phrases["quit"]:
                self.privmsg(p.format(**phrase_data))
        except Exception:
            log.exception("Exception caught while trying to say quit phrase")

        self.twitter_manager.quit()
        self.socket_manager.quit()

        sys.exit(0)

    def apply_filter(self, resp, f: SubstitutionFilter) -> Any:
        available_filters: dict[str, Callable[[Any, List[str]], Any]] = {
            "strftime": _filter_strftime,
            "lower": lambda var, args: var.lower(),
            "upper": lambda var, args: var.upper(),
            "title": lambda var, args: var.title(),
            "capitalize": lambda var, args: var.capitalize(),
            "swapcase": lambda var, args: var.swapcase(),
            "time_since_minutes": lambda var, args: "no time"
            if var == 0
            else utils.time_since(var * 60, 0, time_format="long"),
            "time_since": lambda var, args: "no time" if var == 0 else utils.time_since(var, 0, time_format="long"),
            "time_since_dt": _filter_time_since_dt,
            "timedelta_days": _filter_timedelta_days,
            "urlencode": _filter_urlencode,
            "join": _filter_join,
            "number_format": _filter_number_format,
            "add": _filter_add,
            "or_else": _filter_or_else,
            "or_broadcaster": self._filter_or_broadcaster,
            "or_streamer": self._filter_or_broadcaster,
            "slice": _filter_slice,
            "subtract": _filter_subtract,
            "multiply": _filter_multiply,
            "divide": _filter_divide,
            "floor": _filter_floor,
            "ceil": _filter_ceil,
        }
        if f.name in available_filters:
            return available_filters[f.name](resp, f.arguments)
        return resp

    def _filter_or_broadcaster(self, var: Any, args: List[str]) -> Any:
        return _filter_or_else(var, [self.streamer])

    def find_unique_urls(self, message):
        from pajbot.modules.linkchecker import find_unique_urls

        return find_unique_urls(message)


def _filter_time_since_dt(var: Any, args: List[str]) -> Any:
    try:
        ts = utils.time_since(utils.now().timestamp(), var.timestamp())
        if ts:
            return ts

        return "0 seconds"
    except:
        return "never FeelsBadMan ?"


def _filter_timedelta_days(var: Any, args: List[str]) -> Any:
    try:
        td = utils.now() - var
        return str(td.days)
    except:
        return "0"


def _filter_join(var: Any, args: List[str]) -> Any:
    try:
        separator = args[0]
    except IndexError:
        separator = ", "

    return separator.join(var.split(" "))


def _filter_number_format(var: Any, args: List[str]) -> Any:
    try:
        return f"{int(var):,d}"
    except:
        log.exception("asdasd")
    return var


def _filter_strftime(var: Any, args: List[str]) -> Any:
    return var.strftime(args[0])


def _filter_urlencode(var: Any, args: List[str]) -> Any:
    return urllib.parse.urlencode({"x": var})[2:]


def _filter_add(var: Any, args: List[str]) -> Any:
    try:
        lh = utils.parse_number_from_string(var)
        rh = utils.parse_number_from_string(args[0])

        return str(lh + rh)
    except:
        return ""


def _filter_subtract(var: Any, args: List[str]) -> Any:
    try:
        lh = utils.parse_number_from_string(var)
        rh = utils.parse_number_from_string(args[0])

        return str(lh - rh)
    except:
        return ""


def _filter_multiply(var: Any, args: List[str]) -> Any:
    try:
        lh = utils.parse_number_from_string(var)
        rh = utils.parse_number_from_string(args[0])

        return str(lh * rh)
    except:
        return ""


def _filter_divide(var: Any, args: List[str]) -> Any:
    try:
        lh = utils.parse_number_from_string(var)
        rh = utils.parse_number_from_string(args[0])

        return str(lh / rh)
    except:
        return ""


def _filter_floor(var: Any, args: List[str]) -> Any:
    import math

    try:
        return str(math.floor(float(var)))
    except:
        return ""


def _filter_ceil(var: Any, args: List[str]) -> Any:
    import math

    try:
        return str(math.ceil(float(var)))
    except:
        return ""


def _filter_or_else(var: Any, args: List[str]) -> Any:
    if var is None or len(var) <= 0:
        return args[0]
    else:
        return var


def _filter_slice(var: Any, args: List[str]) -> Any:
    m = SLICE_REGEX.match(args[0])
    if m:
        groups = m.groups()
        if groups[0] is not None and groups[2] is None:
            if groups[1] is None:
                # 0
                return var[slice(int(groups[0]), int(groups[0]) + 1)]

            # 0:
            return var[slice(int(groups[0]), None)]
        if groups[0] is not None and groups[2] is not None:
            # 0:0
            return var[slice(int(groups[0]), int(groups[2]))]

        if groups[0] is None and groups[2] is not None:
            # :0
            return var[slice(int(groups[2]))]

        return var

    return var
