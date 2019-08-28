import cgi
import datetime
import logging
import re
import sys
import time
import urllib
import redis

import irc.client
import requests
from numpy import random
from pytz import timezone

import pajbot.migration_revisions.db
import pajbot.models
import pajbot.models.user
import pajbot.utils
from pajbot.actions import ActionQueue
from pajbot.apiwrappers.authentication.access_token import UserAccessToken
from pajbot.apiwrappers.authentication.client_credentials import ClientCredentials
from pajbot.apiwrappers.authentication.token_manager import AppAccessTokenManager, UserAccessTokenManager
from pajbot.apiwrappers.twitch.helix import TwitchHelixAPI
from pajbot.apiwrappers.twitch.id import TwitchIDAPI
from pajbot.apiwrappers.twitch.kraken_v5 import TwitchKrakenV5API
from pajbot.apiwrappers.twitch.legacy import TwitchLegacyAPI
from pajbot.constants import VERSION
from pajbot.managers.command import CommandManager
from pajbot.managers.db import DBManager
from pajbot.managers.deck import DeckManager
from pajbot.managers.emote import EmoteManager, EpmManager, EcountManager
from pajbot.managers.handler import HandlerManager
from pajbot.managers.irc import IRCManager
from pajbot.managers.kvi import KVIManager
from pajbot.managers.redis import RedisManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.managers.time import TimeManager
from pajbot.managers.twitter import TwitterManager
from pajbot.managers.user import UserManager
from pajbot.managers.websocket import WebSocketManager
from pajbot.migration.db import DatabaseMigratable
from pajbot.migration.migrate import Migration
from pajbot.models.action import ActionParser
from pajbot.models.banphrase import BanphraseManager
from pajbot.models.module import ModuleManager
from pajbot.models.pleblist import PleblistManager
from pajbot.models.sock import SocketManager
from pajbot.models.stream import StreamManager
from pajbot.models.timer import TimerManager
from pajbot.streamhelper import StreamHelper
from pajbot.tmi import TMI
from pajbot.utils import clean_up_message
from pajbot.utils import time_ago
from pajbot.utils import time_method
from pajbot.utils import time_since
from pajbot.utils.extend_version_with_git_data import extend_version_if_possible

log = logging.getLogger(__name__)

URL_REGEX = re.compile(
    r"\(?(?:(http|https):\/\/)?(?:((?:[^\W\s]|\.|-|[:]{1})+)@{1})?((?:www.)?(?:[^\W\s]|\.|-)+[\.][^\W\s]{2,4}|localhost(?=\/)|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::(\d*))?([\/]?[^\s\?]*[\/]{1})*(?:\/?([^\s\n\?\[\]\{\}\#]*(?:(?=\.)){1}|[^\s\n\?\[\]\{\}\.\#]*)?([\.]{1}[^\s\?\#]*)?)?(?:\?{1}([^\s\n\#\[\]]*))?([\#][^\s\n]*)?\)?",
    re.IGNORECASE,
)


class Bot:
    """
    Main class for the twitch bot
    """

    def __init__(self, config, args):
        self.config = config
        self.args = args

        self.last_ping = pajbot.utils.now()
        self.last_pong = pajbot.utils.now()

        DBManager.init(self.config["main"]["db"])

        redis_options = {}

        if "redis" in config:
            redis_options = dict(config.items("redis"))

        RedisManager.init(**redis_options)

        try:
            RedisManager.get().ping()
        except redis.exceptions.BusyLoadingError:
            log.warning("Redis not done loading, waiting 2 seconds then exiting")
            time.sleep(2)
            sys.exit(0)

        pajbot.models.user.Config.se_sync_token = config["main"].get("se_sync_token", None)
        pajbot.models.user.Config.se_channel = config["main"].get("se_channel", None)

        self.domain = config["web"].get("domain", "localhost")
        self.nickname = config["main"].get("nickname", "pajbot")
        self.timezone = config["main"].get("timezone", "UTC")

        if config["main"].getboolean("verified", False):
            TMI.promote_to_verified()
        self.trusted_mods = config.getboolean("main", "trusted_mods")
        self.phrases = {"welcome": ["{nickname} {version} running!"], "quit": ["{nickname} {version} shutting down..."]}
        if "phrases" in config:
            phrases = config["phrases"]
            if "welcome" in phrases:
                self.phrases["welcome"] = phrases["welcome"].splitlines()
            if "quit" in phrases:
                self.phrases["quit"] = phrases["quit"].splitlines()
        TimeManager.init_timezone(self.timezone)
        if "streamer" in config["main"]:
            self.streamer = config["main"]["streamer"]
            self.channel = "#" + self.streamer
        elif "target" in config["main"]:
            self.channel = config["main"]["target"]
            self.streamer = self.channel[1:]
        StreamHelper.init_streamer(self.streamer)

        log.debug("Loaded config")

        # streamer is additionally initialized here so streamer can be accessed by the DB migrations
        # before StreamHelper.init_bot() is called later (which depends on an upgraded DB because
        # StreamManager accesses the DB)
        StreamHelper.init_streamer(self.streamer)

        # do this earlier since schema upgrade can depend on the helix api
        self.api_client_credentials = ClientCredentials(
            self.config["twitchapi"]["client_id"],
            self.config["twitchapi"]["client_secret"],
            self.config["twitchapi"]["redirect_uri"],
        )

        self.twitch_id_api = TwitchIDAPI(self.api_client_credentials)
        self.app_token_manager = AppAccessTokenManager(self.twitch_id_api, RedisManager.get())
        self.twitch_helix_api = TwitchHelixAPI(RedisManager.get(), self.app_token_manager)
        self.twitch_v5_api = TwitchKrakenV5API(self.api_client_credentials, RedisManager.get())
        self.twitch_legacy_api = TwitchLegacyAPI(self.api_client_credentials, RedisManager.get())

        self.bot_user_id = self.twitch_helix_api.get_user_id(self.nickname)
        if self.bot_user_id is None:
            raise ValueError("The bot nickname you entered under [main] does not exist on twitch.")

        self.streamer_user_id = self.twitch_helix_api.get_user_id(self.streamer)
        if self.bot_user_id is None:
            raise ValueError("The bot nickname you entered under [main] does not exist on twitch.")

        sql_conn = DBManager.engine.connect().connection
        sql_migratable = DatabaseMigratable(sql_conn)
        sql_migration = Migration(sql_migratable, pajbot.migration_revisions.db, self)
        sql_migration.run()

        # Actions in this queue are run in a separate thread.
        # This means actions should NOT access any database-related stuff.
        self.action_queue = ActionQueue()
        self.action_queue.start()

        self.reactor = irc.client.Reactor(self.on_connect)
        self.start_time = pajbot.utils.now()
        ActionParser.bot = self

        HandlerManager.init_handlers()

        self.socket_manager = SocketManager(self.streamer, self.execute_now)
        self.stream_manager = StreamManager(self)

        StreamHelper.init_bot(self, self.stream_manager)
        ScheduleManager.init()

        self.users = UserManager()
        self.decks = DeckManager()
        self.banphrase_manager = BanphraseManager(self).load()
        self.timer_manager = TimerManager(self).load()
        self.kvi = KVIManager()

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

        self.emote_manager = EmoteManager(self.twitch_v5_api, self.twitch_legacy_api, self.action_queue)
        self.epm_manager = EpmManager()
        self.ecount_manager = EcountManager()
        self.twitter_manager = TwitterManager(self)

        self.module_manager = ModuleManager(self.socket_manager, bot=self).load()
        self.commands = CommandManager(
            socket_manager=self.socket_manager, module_manager=self.module_manager, bot=self
        ).load()

        HandlerManager.trigger("on_managers_loaded")

        # Commitable managers
        self.commitable = {"commands": self.commands, "banphrases": self.banphrase_manager}

        self.execute_every(10 * 60, self.commit_all)
        self.execute_every(1, self.do_tick)

        # promote the admin to level 2000
        admin = None
        try:
            admin = self.config["main"]["admin"]
        except KeyError:
            log.warning("No admin user specified. See the [main] section in the example config for its usage.")
        if admin is not None:
            with self.users.get_user_context(admin) as user:
                user.level = 2000

        # silent mode
        self.silent = (
            "flags" in config and "silent" in config["flags"] and config["flags"]["silent"] == "1"
        ) or args.silent
        if self.silent:
            log.info("Silent mode enabled")

        # dev mode
        self.dev = "flags" in config and "dev" in config["flags"] and config["flags"]["dev"] == "1"
        if self.dev:
            self.version_long = extend_version_if_possible(VERSION)
        else:
            self.version_long = VERSION

        self.irc = IRCManager(self)

        relay_host = self.config["main"].get("relay_host", None)
        relay_password = self.config["main"].get("relay_password", None)
        if relay_host is not None or relay_password is not None:
            log.warning(
                "DEPRECATED - Relaybroker support is no longer implemented. relay_host and relay_password are ignored"
            )

        self.reactor.add_global_handler("all_events", self.irc._dispatcher, -10)

        self.data = {
            "broadcaster": self.streamer,
            "version": self.version_long,
            "version_brief": VERSION,
            "bot_name": self.nickname,
        }

        self.data_cb = {
            "status_length": self.c_status_length,
            "stream_status": self.c_stream_status,
            "bot_uptime": self.c_uptime,
            "current_time": self.c_current_time,
            "molly_age_in_years": self.c_molly_age_in_years,
        }

        self.websocket_manager = WebSocketManager(self)

    @property
    def password(self):
        return "oauth:{}".format(self.bot_token_manager.token.access_token)

    def on_connect(self, sock):
        return self.irc.on_connect(sock)

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
        return "{0:,.0f}".format(epm)

    def get_emote_epm_record(self, key, extra={}):
        val = self.epm_manager.get_emote_epm_record(key)
        if val is None:
            return None
        # formats the number with grouping (e.g. 112,556) and zero decimal places
        return "{0:,.0f}".format(val)

    def get_emote_count(self, key, extra={}):
        val = self.ecount_manager.get_emote_count(key)
        if val is None:
            return None
        # formats the number with grouping (e.g. 112,556) and zero decimal places
        return "{0:,.0f}".format(val)

    @staticmethod
    def get_source_value(key, extra={}):
        try:
            return getattr(extra["source"], key)
        except:
            log.exception("Caught exception in get_source_value")

        return None

    def get_user_value(self, key, extra={}):
        try:
            user = self.users.find(extra["argument"])
            if user:
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

    def get_usersource_value(self, key, extra={}):
        try:
            user = self.users.find(extra["argument"])
            if user:
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

    def get_notify_value(self, key, extra={}):
        payload = {"message": extra["message"] or "", "trigger": extra["trigger"], "user": extra["source"].username_raw}
        self.websocket_manager.emit("notify", payload)

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

    def privmsg_from_file(self, url, per_chunk=35, chunk_delay=30, target=None):
        try:
            r = requests.get(url)
            r.raise_for_status()

            content_type = r.headers["Content-Type"]
            if content_type is not None and cgi.parse_header(content_type)[0] != "text/plain":
                log.error("privmsg_from_file should be fed with a text/plain URL. Refusing to send.")
                return

            lines = r.text.splitlines()
            i = 0
            while lines:
                if i == 0:
                    self.privmsg_arr(lines[:per_chunk], target)
                else:
                    self.execute_delayed(chunk_delay * i, self.privmsg_arr, (lines[:per_chunk], target))

                del lines[:per_chunk]

                i = i + 1
        except:
            log.exception("error in privmsg_from_file")

    # event is an event to clone and change the text from.
    # Usage: !eval bot.eval_from_file(event, 'https://pastebin.com/raw/LhCt8FLh')
    def eval_from_file(self, event, url):
        try:
            r = requests.get(url)
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
            self.whisper(event.source.user.lower(), "Successfully evaluated {0} lines".format(len(lines)))
        except:
            log.exception("BabyRage")
            self.whisper(event.source.user.lower(), "Exception BabyRage")

    def privmsg(self, message, channel=None, increase_message=True):
        if channel is None:
            channel = self.channel

        return self.irc.privmsg(message, channel, increase_message=increase_message)

    def c_uptime(self):
        return time_ago(self.start_time)

    @staticmethod
    def c_current_time():
        return pajbot.utils.now()

    @staticmethod
    def c_molly_age_in_years():
        molly_birth = datetime.datetime(2018, 10, 29, tzinfo=datetime.timezone.utc)
        now = pajbot.utils.now()
        diff = now - molly_birth
        return diff.total_seconds() / 3600 / 24 / 365

    @property
    def is_online(self):
        return self.stream_manager.online

    def c_stream_status(self):
        return "online" if self.stream_manager.online else "offline"

    def c_status_length(self):
        if self.stream_manager.online:
            return time_ago(self.stream_manager.current_stream.stream_start)

        if self.stream_manager.last_stream is not None:
            return time_ago(self.stream_manager.last_stream.stream_end)

        return "No recorded stream FeelsBadMan "

    def execute_now(self, function, arguments=()):
        self.execute_delayed(0, function, arguments)

    def execute_at(self, at, function, arguments=()):
        self.reactor.scheduler.execute_at(at, lambda: function(*arguments))

    def execute_delayed(self, delay, function, arguments=()):
        self.reactor.scheduler.execute_after(delay, lambda: function(*arguments))

    def execute_every(self, period, function, arguments=()):
        self.reactor.scheduler.execute_every(period, lambda: function(*arguments))

    def _ban(self, username, reason=""):
        self.privmsg(".ban {0} {1}".format(username, reason), increase_message=False)

    def ban(self, username, reason=""):
        log.debug("Banning %s", username)
        self._timeout(username, 30, reason)
        self.execute_delayed(1, self._ban, (username, reason))

    def ban_user(self, user, reason=""):
        self._timeout(user.username, 30, reason)
        self.execute_delayed(1, self._ban, (user.username, reason))

    def unban(self, username):
        self.privmsg(".unban {0}".format(username), increase_message=False)

    def _timeout(self, username, duration, reason=""):
        self.privmsg(".timeout {0} {1} {2}".format(username, duration, reason), increase_message=False)

    def timeout(self, username, duration, reason=""):
        log.debug("Timing out %s for %d seconds", username, duration)
        self._timeout(username, duration, reason)
        self.execute_delayed(1, self._timeout, (username, duration, reason))

    def timeout_warn(self, user, duration, reason=""):
        duration, punishment = user.timeout(duration, warning_module=self.module_manager["warning"])
        self.timeout(user.username, duration, reason)
        return (duration, punishment)

    def timeout_user(self, user, duration, reason=""):
        self._timeout(user.username, duration, reason)
        self.execute_delayed(1, self._timeout, (user.username, duration, reason))

    def timeout_user_once(self, user, duration, reason):
        self._timeout(user.username, duration, reason)

    def _timeout_user(self, user, duration, reason=""):
        self._timeout(user.username, duration, reason)

    def delete_message(self, msg_id):
        self.privmsg(".delete {0}".format(msg_id))

    def whisper(self, username, *messages, separator=". ", **rest):
        """
        Takes a sequence of strings and concatenates them with separator.
        Then sends that string as a whisper to username
        """

        if len(messages) < 0:
            return False

        message = separator.join(messages)

        return self.irc.whisper(username, message)

    def send_message_to_user(self, user, message, event, separator=". ", method="say"):
        if method == "say":
            self.say(user.username + ", " + lowercase_first_letter(message), separator=separator)
        elif method == "whisper":
            self.whisper(user.username, message, separator=separator)
        elif method == "me":
            self.me(message)
        elif method == "reply":
            if event.type in ["action", "pubmsg"]:
                self.say(message, separator=separator)
            elif event.type == "whisper":
                self.whisper(user.username, message, separator=separator)
        else:
            log.warning("Unknown send_message method: %s", method)

    def safe_privmsg(self, message, channel=None, increase_message=True):
        # Check for banphrases
        res = self.banphrase_manager.check_message(message, None)
        if res is not False:
            self.privmsg("filtered message ({})".format(res.id), channel, increase_message)
            return

        self.privmsg(message, channel, increase_message)

    def say(self, *messages, channel=None, separator=". "):
        """
        Takes a sequence of strings and concatenates them with separator.
        Then sends that string to the given channel.
        """

        if len(messages) < 0:
            return False

        if not self.silent:
            message = separator.join(messages).strip()

            message = clean_up_message(message)
            if not message:
                return False

            log.info("Sending message: %s", message)

            self.privmsg(message[:510], channel)

    def is_bad_message(self, message):
        return self.banphrase_manager.check_message(message, None) is not False

    def safe_me(self, message, channel=None):
        if not self.is_bad_message(message):
            self.me(message, channel)

    def me(self, message, channel=None):
        self.say(".me " + message[:500], channel=channel)

    def on_welcome(self, chatconn, event):
        return self.irc.on_welcome(chatconn, event)

    def connect(self):
        return self.irc.start()

    def on_disconnect(self, chatconn, event):
        self.irc.on_disconnect(chatconn, event)

    def parse_message(self, message, source, event, tags={}, whisper=False):
        msg_lower = message.lower()

        emote_tag = None
        msg_id = None

        for tag in tags:
            if tag["key"] == "subscriber" and event.target == self.channel:
                source.subscriber = tag["value"] == "1"
            elif tag["key"] == "emotes":
                emote_tag = tag["value"]
            elif tag["key"] == "display-name" and tag["value"]:
                source.username_raw = tag["value"]
            elif tag["key"] == "user-type":
                source.moderator = tag["value"] == "mod" or source.username == self.streamer
            elif tag["key"] == "id":
                msg_id = tag["value"]

        # source.num_lines += 1

        if source is None:
            log.error("No valid user passed to parse_message")
            return False

        if source.banned:
            self.ban(source.username)
            return False

        # If a user types when timed out, we assume he's been unbanned for a good reason and remove his flag.
        if source.timed_out is True:
            source.timed_out = False

        # Parse emotes in the message
        emote_instances, emote_counts = self.emote_manager.parse_all_emotes(message, emote_tag)

        if not whisper:
            # increment epm and ecount
            self.epm_manager.handle_emotes(emote_counts)
            self.ecount_manager.handle_emotes(emote_counts)

        urls = self.find_unique_urls(message)

        log.debug("{2}{0}: {1}".format(source.username, message, "<w>" if whisper else ""))

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

        source.last_seen = pajbot.utils.now()
        source.last_active = pajbot.utils.now()

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
        # We use .lower() in case twitch ever starts sending non-lowercased usernames
        username = event.source.user.lower()

        with self.users.get_user_context(username) as source:
            self.parse_message(event.arguments[0], source, event, whisper=True, tags=event.tags)

    def on_ping(self, chatconn, event):
        # self.say('Received a ping. Last ping received {} ago'.format(time_since(pajbot.utils.now().timestamp(), self.last_ping.timestamp())))
        log.info("Received a ping. Last ping received %s ago", time_ago(self.last_ping))
        self.last_ping = pajbot.utils.now()

    def on_pong(self, chatconn, event):
        # self.say('Received a pong. Last pong received {} ago'.format(time_since(pajbot.utils.now().timestamp(), self.last_pong.timestamp())))
        log.info("Received a pong. Last pong received %s ago", time_ago(self.last_pong))
        self.last_pong = pajbot.utils.now()

    def on_usernotice(self, chatconn, event):
        # We use .lower() in case twitch ever starts sending non-lowercased usernames
        tags = {}
        for d in event.tags:
            tags[d["key"]] = d["value"]

        if "login" not in tags:
            return

        username = tags["login"]

        with self.users.get_user_context(username) as source:
            msg = ""
            if event.arguments:
                msg = event.arguments[0]
            HandlerManager.trigger("on_usernotice", source=source, message=msg, tags=tags)

    def on_action(self, chatconn, event):
        self.on_pubmsg(chatconn, event)

    def on_pubmsg(self, chatconn, event):
        if event.source.user == self.nickname:
            return False

        username = event.source.user.lower()

        if self.streamer == "forsen":
            if "zonothene" in username:
                self._ban(username)
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
            if "hades_k" in username:
                self._timeout(username, 3600)
                return True

            if "hades_b" in username:
                self._timeout(username, 3600)
                return True

        # We use .lower() in case twitch ever starts sending non-lowercased usernames
        with self.users.get_user_context(username) as source:
            res = HandlerManager.trigger("on_pubmsg", source=source, message=event.arguments[0])
            if res is False:
                return False

            self.parse_message(event.arguments[0], source, event, tags=event.tags)

    @time_method
    def commit_all(self):
        log.info("Commiting all...")
        for key, manager in self.commitable.items():
            log.info("Commiting %s", key)
            manager.commit()
            log.info("Done with %s", key)
        log.info("ok!")

        HandlerManager.trigger("on_commit", stop_on_false=False)

    @staticmethod
    def do_tick():
        HandlerManager.trigger("on_tick")

    def quit(self, message, event, **options):
        quit_chub = self.config["main"].get("control_hub", None)
        quit_delay = 0

        if quit_chub is not None and event.target == ("#{}".format(quit_chub)):
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
        phrase_data = {"nickname": self.nickname, "version": self.version}

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

    def apply_filter(self, resp, f):
        available_filters = {
            "strftime": _filter_strftime,
            "lower": lambda var, args: var.lower(),
            "upper": lambda var, args: var.upper(),
            "time_since_minutes": lambda var, args: "no time"
            if var == 0
            else time_since(var * 60, 0, time_format="long"),
            "time_since": lambda var, args: "no time" if var == 0 else time_since(var, 0, time_format="long"),
            "time_since_dt": _filter_time_since_dt,
            "urlencode": _filter_urlencode,
            "join": _filter_join,
            "number_format": _filter_number_format,
            "add": _filter_add,
            "or_else": _filter_or_else,
            "or_broadcaster": self._filter_or_broadcaster,
            "or_streamer": self._filter_or_broadcaster,
        }
        if f.name in available_filters:
            return available_filters[f.name](resp, f.arguments)
        return resp

    def _filter_or_broadcaster(self, var, args):
        return _filter_or_else(var, self.streamer)

    def find_unique_urls(self, message):
        from pajbot.modules.linkchecker import find_unique_urls

        return find_unique_urls(URL_REGEX, message)


def _filter_time_since_dt(var, args):
    try:
        ts = time_since(pajbot.utils.now().timestamp(), var.timestamp())
        if ts:
            return ts

        return "0 seconds"
    except:
        return "never FeelsBadMan ?"


def _filter_join(var, args):
    try:
        separator = args[0]
    except IndexError:
        separator = ", "

    return separator.join(var.split(" "))


def _filter_number_format(var, args):
    try:
        return "{0:,d}".format(int(var))
    except:
        log.exception("asdasd")
    return var


def _filter_strftime(var, args):
    return var.strftime(args[0])


def _filter_urlencode(var, args):
    return urllib.parse.urlencode({"x": var})[2:]


def lowercase_first_letter(s):
    return s[:1].lower() + s[1:] if s else ""


def _filter_add(var, args):
    try:
        return str(int(var) + int(args[0]))
    except:
        return ""


def _filter_or_else(var, args):
    if var is None or len(var) <= 0:
        return args[0]
    else:
        return var
