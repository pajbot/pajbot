import argparse
import datetime
import logging
import re
import subprocess
import sys
import time
import urllib

import irc.client
from numpy import random
from pytz import timezone

import pajbot.utils
from pajbot.actions import ActionQueue
from pajbot.apiwrappers import TwitchAPI
from pajbot.managers import DBManager
from pajbot.managers import DeckManager
from pajbot.managers import EmoteManager
from pajbot.managers import FilterManager
from pajbot.managers import HandlerManager
from pajbot.managers import KVIManager
from pajbot.managers import MultiIRCManager
from pajbot.managers import RedisManager
from pajbot.managers import ScheduleManager
from pajbot.managers import SingleIRCManager
from pajbot.managers import TimeManager
from pajbot.managers import TwitterManager
from pajbot.managers import WebSocketManager
from pajbot.models.action import ActionParser
from pajbot.models.banphrase import BanphraseManager
from pajbot.models.command import CommandManager
from pajbot.models.duel import DuelManager
from pajbot.models.module import ModuleManager
from pajbot.models.pleblist import PleblistManager
from pajbot.models.sock import SocketManager
from pajbot.models.stream import StreamManager
from pajbot.models.timer import TimerManager
from pajbot.models.user import UserManager
from pajbot.streamhelper import StreamHelper
from pajbot.tbutil import time_method
from pajbot.tbutil import time_since

log = logging.getLogger(__name__)


class TMI:
    message_limit = 90
    whispers_message_limit = 20
    whispers_limit_interval = 5  # in seconds


class Bot:
    """
    Main class for the twitch bot
    """

    version = '2.7.4'
    date_fmt = '%H:%M'
    admin = None
    url_regex_str = r'\(?(?:(http|https):\/\/)?(?:((?:[^\W\s]|\.|-|[:]{1})+)@{1})?((?:www.)?(?:[^\W\s]|\.|-)+[\.][^\W\s]{2,4}|localhost(?=\/)|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::(\d*))?([\/]?[^\s\?]*[\/]{1})*(?:\/?([^\s\n\?\[\]\{\}\#]*(?:(?=\.)){1}|[^\s\n\?\[\]\{\}\.\#]*)?([\.]{1}[^\s\?\#]*)?)?(?:\?{1}([^\s\n\#\[\]]*))?([\#][^\s\n]*)?\)?'

    last_ping = datetime.datetime.now()
    last_pong = datetime.datetime.now()

    def parse_args():
        parser = argparse.ArgumentParser()
        parser.add_argument('--config', '-c',
                            default='config.ini',
                            help='Specify which config file to use '
                                    '(default: config.ini)')
        parser.add_argument('--silent',
                            action='count',
                            help='Decides whether the bot should be '
                            'silent or not')
        # TODO: Add a log level argument.

        return parser.parse_args()

    def load_config(self, config):
        self.config = config

        self.domain = config['web'].get('domain', 'localhost')

        self.nickname = config['main'].get('nickname', 'pajbot')
        self.password = config['main'].get('password', 'abcdef')

        self.timezone = config['main'].get('timezone', 'UTC')

        self.trusted_mods = config.getboolean('main', 'trusted_mods')

        TimeManager.init_timezone(self.timezone)

        if 'streamer' in config['main']:
            self.streamer = config['main']['streamer']
            self.channel = '#' + self.streamer
        elif 'target' in config['main']:
            self.channel = config['main']['target']
            self.streamer = self.channel[1:]

        self.wolfram = None
        try:
            if 'wolfram' in config['main']:
                import wolframalpha
                self.wolfram = wolframalpha.Client(config['main']['wolfram'])
        except:
            pass

        self.silent = False
        self.dev = False

        if 'flags' in config:
            self.silent = True if 'silent' in config['flags'] and config['flags']['silent'] == '1' else self.silent
            self.dev = True if 'dev' in config['flags'] and config['flags']['dev'] == '1' else self.dev

        DBManager.init(self.config['main']['db'])

        redis_options = {}
        if 'redis' in config:
            redis_options = config._sections['redis']

        RedisManager.init(**redis_options)

    def __init__(self, config, args=None):
        # Load various configuration variables from the given config object
        # The config object that should be passed through should
        # come from pajbot.tbutil.load_config
        self.load_config(config)

        # Update the database scheme if necessary using alembic
        # In case of errors, i.e. if the database is out of sync or the alembic
        # binary can't be called, we will shut down the bot.
        pajbot.utils.alembic_upgrade()

        # Actions in this queue are run in a separate thread.
        # This means actions should NOT access any database-related stuff.
        self.action_queue = ActionQueue()
        self.action_queue.start()

        self.reactor = irc.client.Reactor(self.on_connect)
        self.start_time = datetime.datetime.now()
        ActionParser.bot = self

        HandlerManager.init_handlers()

        self.socket_manager = SocketManager(self)
        self.stream_manager = StreamManager(self)

        StreamHelper.init_bot(self, self.stream_manager)
        ScheduleManager.init()

        self.users = UserManager()
        self.decks = DeckManager()
        self.module_manager = ModuleManager(self.socket_manager, bot=self).load()
        self.commands = CommandManager(
                socket_manager=self.socket_manager,
                module_manager=self.module_manager,
                bot=self).load()
        self.filters = FilterManager().reload()
        self.banphrase_manager = BanphraseManager(self).load()
        self.timer_manager = TimerManager(self).load()
        self.kvi = KVIManager()
        self.emotes = EmoteManager(self)
        self.twitter_manager = TwitterManager(self)
        self.duel_manager = DuelManager(self)

        HandlerManager.trigger('on_managers_loaded')

        # Reloadable managers
        self.reloadable = {
                'filters': self.filters,
                }

        # Commitable managers
        self.commitable = {
                'commands': self.commands,
                'filters': self.filters,
                'users': self.users,
                'banphrases': self.banphrase_manager,
                }

        self.execute_every(10 * 60, self.commit_all)

        try:
            self.admin = self.config['main']['admin']
        except KeyError:
            log.warning('No admin user specified. See the [main] section in config.example.ini for its usage.')
        if self.admin:
            self.users[self.admin].level = 2000

        self.parse_version()

        relay_host = self.config['main'].get('relay_host', None)
        relay_password = self.config['main'].get('relay_password', None)
        if relay_host is None or relay_password is None:
            self.irc = MultiIRCManager(self)
        else:
            self.irc = SingleIRCManager(self)

        self.reactor.add_global_handler('all_events', self.irc._dispatcher, -10)

        twitch_client_id = None
        twitch_oauth = None
        if 'twitchapi' in self.config:
            twitch_client_id = self.config['twitchapi'].get('client_id', None)
            twitch_oauth = self.config['twitchapi'].get('oauth', None)

        self.twitchapi = TwitchAPI(twitch_client_id, twitch_oauth)

        self.ascii_timeout_duration = 120
        self.msg_length_timeout_duration = 120

        self.data = {}
        self.data_cb = {}
        self.url_regex = re.compile(self.url_regex_str, re.IGNORECASE)

        self.data['broadcaster'] = self.streamer
        self.data['version'] = self.version
        self.data_cb['status_length'] = self.c_status_length
        self.data_cb['stream_status'] = self.c_stream_status
        self.data_cb['bot_uptime'] = self.c_uptime
        self.data_cb['current_time'] = self.c_current_time

        self.silent = True if args.silent else self.silent

        if self.silent:
            log.info('Silent mode enabled')

        self.reconnection_interval = 5

        """
        For actions that need to access the main thread,
        we can use the mainthread_queue.
        """
        self.mainthread_queue = ActionQueue()
        self.execute_every(1, self.mainthread_queue.parse_action)

        self.websocket_manager = WebSocketManager(self)

        try:
            if self.config['twitchapi']['update_subscribers'] == '1':
                self.execute_every(30 * 60,
                                   self.action_queue.add,
                                   (self.update_subscribers_stage1, ))
        except:
            pass

        # XXX: TEMPORARY UGLY CODE
        HandlerManager.add_handler('on_user_gain_tokens', self.on_user_gain_tokens)

    def on_connect(self, sock):
        return self.irc.on_connect(sock)

    def on_user_gain_tokens(self, user, tokens_gained):
        self.whisper(user.username, 'You finished todays quest! You have been awarded with {} tokens.'.format(tokens_gained))

    def update_subscribers_stage1(self):
        limit = 100
        offset = 0
        subscribers = []
        log.info('Starting stage1 subscribers update')

        try:
            retry_same = 0
            while True:
                log.debug('Beginning sub request {0} {1}'.format(limit, offset))
                subs, retry_same, error = self.twitchapi.get_subscribers(self.streamer, limit, offset, 0 if retry_same is False else retry_same)
                log.debug('got em!')

                if error is True:
                    log.error('Too many attempts, aborting')
                    return False

                if retry_same is False:
                    offset += limit
                    if len(subs) == 0:
                        # We don't need to retry, and the last query finished propery
                        # Break out of the loop and start fiddling with the subs!
                        log.debug('Done!')
                        break
                    else:
                        log.debug('Fetched {0} subs'.format(len(subs)))
                        subscribers.extend(subs)

                if retry_same is not False:
                    # In case the next attempt is a retry, wait for 3 seconds
                    log.debug('waiting for 3 seconds...')
                    time.sleep(3)
                    log.debug('waited enough!')
            log.debug('Finished with the while True loop!')
        except:
            log.exception('Caught an exception while trying to get subscribers')
            return

        log.info('Ended stage1 subscribers update')
        if len(subscribers) > 0:
            log.info('Got some subscribers, so we are pushing them to stage 2!')
            self.mainthread_queue.add(self.update_subscribers_stage2,
                                      args=[subscribers])
            log.info('Pushed them now.')

    def update_subscribers_stage2(self, subscribers):
        log.debug('begiunning stage 2 of update subs')
        self.kvi['active_subs'].set(len(subscribers) - 1)

        log.debug('Bulk loading subs...')
        loaded_subscribers = self.users.bulk_load(subscribers)
        log.debug('ok!')

        log.debug('settings all loaded users as non-subs')
        self.users.reset_subs()
        """
        for username, user in self.users.items():
            if user.subscriber:
                user.subscriber = False
                """

        log.debug('ok!, setting loaded subs as subs')
        for user in loaded_subscribers:
            user.subscriber = True

        log.debug('end of stage 2 of update subs')

    def start(self):
        """Start the IRC client."""
        self.reactor.process_forever()

    def get_kvi_value(self, key, extra={}):
        return self.kvi[key].get()

    def get_last_tweet(self, key, extra={}):
        return self.twitter_manager.get_last_tweet(key)

    def get_emote_tm(self, key, extra={}):
        val = self.emotes.get_emote_epm(key)
        if not val:
            return None
        return '{0:,d}'.format(val)

    def get_emote_count(self, key, extra={}):
        val = self.emotes.get_emote_count(key)
        if not val:
            return None
        return '{0:,d}'.format(val)

    def get_emote_tm_record(self, key, extra={}):
        val = self.emotes.get_emote_epmrecord(key)
        if not val:
            return None
        return '{0:,d}'.format(val)

    def get_source_value(self, key, extra={}):
        try:
            return getattr(extra['source'], key)
        except:
            log.exception('Caught exception in get_source_value')

        return None

    def get_user_value(self, key, extra={}):
        try:
            user = self.users.find(extra['argument'])
            if user:
                return getattr(user, key)
        except:
            log.exception('Caught exception in get_source_value')

        return None

    def get_usersource_value(self, key, extra={}):
        try:
            user = self.users.find(extra['argument'])
            if user:
                return getattr(user, key)
            else:
                return getattr(extra['source'], key)
        except:
            log.exception('Caught exception in get_source_value')

        return None

    def get_time_value(self, key, extra={}):
        try:
            tz = timezone(key)
            return datetime.datetime.now(tz).strftime(self.date_fmt)
        except:
            log.exception('Unhandled exception in get_time_value')

        return None

    def get_current_song_value(self, key, extra={}):
        if self.stream_manager.online:
            current_song = PleblistManager.get_current_song(self.stream_manager.current_stream.id)
            inner_keys = key.split('.')
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

        if len(ret) == 0:
            return None
        return ret

    def get_args_value(self, key, extra={}):
        range = None
        try:
            msg_parts = extra['message'].split(' ')
        except (KeyError, AttributeError):
            msg_parts = ['']

        try:
            if '-' in key:
                range_str = key.split('-')
                if len(range_str) == 2:
                    range = (int(range_str[0]), int(range_str[1]))

            if range is None:
                range = (int(key), len(msg_parts))
        except (TypeError, ValueError):
            range = (0, len(msg_parts))

        try:
            return ' '.join(msg_parts[range[0]:range[1]])
        except AttributeError:
            return ''
        except:
            log.exception('UNHANDLED ERROR IN get_args_value')
            return ''

    def get_notify_value(self, key, extra={}):
        payload = {
                'message': extra['message'] or '',
                'trigger': extra['trigger'],
                'user': extra['source'].username_raw,
                }
        self.websocket_manager.emit('notify', payload)

        return ''

    def get_value(self, key, extra={}):
        if key in extra:
            return extra[key]
        elif key in self.data:
            return self.data[key]
        elif key in self.data_cb:
            return self.data_cb[key]()

        log.warning('Unknown key passed to get_value: {0}'.format(key))
        return None

    def privmsg(self, message, channel=None, increase_message=True):
        if channel is None:
            channel = self.channel

        return self.irc.privmsg(message, channel, increase_message=increase_message)

    def c_uptime(self):
        return time_since(datetime.datetime.now().timestamp(), self.start_time.timestamp())

    def c_current_time(self):
        return datetime.datetime.now()

    @property
    def is_online(self):
        return self.stream_manager.online

    def c_stream_status(self):
        return 'online' if self.stream_manager.online else 'offline'

    def c_status_length(self):
        if self.stream_manager.online:
            return time_since(time.time(), self.stream_manager.current_stream.stream_start.timestamp())
        else:
            if self.stream_manager.last_stream is not None:
                return time_since(time.time(), self.stream_manager.last_stream.stream_end.timestamp())
            else:
                return 'No recorded stream FeelsBadMan '

    def _ban(self, username):
        self.privmsg('.ban {0}'.format(username), increase_message=False)

    def execute_at(self, at, function, arguments=()):
        self.reactor.execute_at(at, function, arguments)

    def execute_delayed(self, delay, function, arguments=()):
        self.reactor.execute_delayed(delay, function, arguments)

    def execute_every(self, period, function, arguments=()):
        self.reactor.execute_every(period, function, arguments)

    def ban(self, username):
        log.debug('Banning {}'.format(username))
        self._timeout(username, 30)
        self.execute_delayed(1, self._ban, (username, ))

    def ban_user(self, user):
        if not user.ban_immune:
            self._timeout(user.username, 30)
            self.execute_delayed(1, self._ban, (user.username, ))

    def unban(self, username):
        self.privmsg('.unban {0}'.format(username), increase_message=False)

    def _timeout(self, username, duration):
        self.privmsg('.timeout {0} {1}'.format(username, duration), increase_message=False)

    def timeout(self, username, duration):
        log.debug('Timing out {} for {} seconds'.format(username, duration))
        self._timeout(username, duration)
        self.execute_delayed(1, self._timeout, (username, duration))

    def timeout_warn(self, user, duration):
        duration, punishment = user.timeout(duration, warning_module=self.module_manager['warning'])
        if not user.ban_immune:
            self.timeout(user.username, duration)
            return (duration, punishment)
        return (0, punishment)

    def timeout_user(self, user, duration):
        if not user.ban_immune:
            self._timeout(user.username, duration)
            self.execute_delayed(1, self._timeout, (user.username, duration))

    def whisper(self, username, *messages, separator='. '):
        """
        Takes a sequence of strings and concatenates them with separator.
        Then sends that string as a whisper to username
        """

        if len(messages) < 0:
            return False

        message = separator.join(messages)

        return self.irc.whisper(username, message)

    def say(self, *messages, channel=None, separator='. '):
        """
        Takes a sequence of strings and concatenates them with separator.
        Then sends that string to the given channel.
        """

        if len(messages) < 0:
            return False

        if not self.silent:
            message = separator.join(messages).strip()

            if len(message) >= 1:
                if (message[0] == '.' or message[0] == '/') and not message[1:3] == 'me':
                    log.warning('Message we attempted to send started with . or /, skipping.')
                    return

                log.info('Sending message: {0}'.format(message))

                self.privmsg(message[:510], channel)

    def me(self, message, channel=None):
        if not self.silent:
            message = message.strip()

            if len(message) >= 1:
                if message[0] == '.' or message[0] == '/':
                    log.warning('Message we attempted to send started with . or /, skipping.')
                    return

                log.info('Sending message: {0}'.format(message))

                self.privmsg('.me ' + message[:500], channel)

    def parse_version(self):
        self.version = self.version

        if self.dev:
            try:
                current_branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode('utf8').strip()
                latest_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf8').strip()[:8]
                commit_number = subprocess.check_output(['git', 'rev-list', 'HEAD', '--count']).decode('utf8').strip()
                self.version = '{0} DEV ({1}, {2}, commit {3})'.format(self.version, current_branch, latest_commit, commit_number)
            except:
                pass

    def on_welcome(self, chatconn, event):
        return self.irc.on_welcome(chatconn, event)

    def connect(self):
        return self.irc.start()

    def on_disconnect(self, chatconn, event):
        self.irc.on_disconnect(chatconn, event)

    def parse_message(self, msg_raw, source, event, tags={}, whisper=False):
        msg_lower = msg_raw.lower()

        if source is None:
            log.error('No valid user passed to parse_message')
            return False

        if source.banned:
            self.ban(source.username)
            return False

        # If a user types when timed out, we assume he's been unbanned for a good reason and remove his flag.
        if source.timed_out is True:
            source.timed_out = False

        emote_tag = None
        for tag in tags:
            if tag['key'] == 'subscriber' and event.target == self.channel:
                if source.subscriber and tag['value'] == '0':
                    source.subscriber = False
                elif not source.subscriber and tag['value'] == '1':
                    source.subscriber = True
            elif tag['key'] == 'emotes' and tag['value']:
                emote_tag = tag['value']
            elif tag['key'] == 'display-name' and tag['value']:
                try:
                    source.update_username(tag['value'])
                except:
                    log.exception('Exception caught while updating a users username')
            elif tag['key'] == 'user-type':
                source.moderator = tag['value'] == 'mod' or source.username == self.streamer

        # Parse emotes in the message
        message_emotes = self.emotes.parse_message_twitch_emotes(source, msg_raw, emote_tag)

        urls = self.find_unique_urls(msg_raw)

        log.debug('{2}{0}: {1}'.format(source.username, msg_raw, '<w>' if whisper else ''))

        res = HandlerManager.trigger('on_message',
                source, msg_raw, message_emotes, whisper, urls, event,
                stop_on_false=True)
        if res is False:
            return False

        source.last_seen = datetime.datetime.now()
        source.last_active = datetime.datetime.now()

        if source.ignored:
            return False

        if msg_lower[:1] == '!':
            msg_lower_parts = msg_lower.split(' ')
            trigger = msg_lower_parts[0][1:]
            msg_raw_parts = msg_raw.split(' ')
            remaining_message = ' '.join(msg_raw_parts[1:]) if len(msg_raw_parts) > 1 else None
            if trigger in self.commands:
                command = self.commands[trigger]
                extra_args = {
                        'emotes': message_emotes,
                        'trigger': trigger,
                        }
                command.run(self, source, remaining_message, event=event, args=extra_args, whisper=whisper)

    def on_whisper(self, chatconn, event):
        # We use .lower() in case twitch ever starts sending non-lowercased usernames
        source = self.users[event.source.user.lower()]
        self.parse_message(event.arguments[0], source, event, whisper=True, tags=event.tags)

    def on_ping(self, chatconn, event):
        # self.say('Received a ping. Last ping received {} ago'.format(time_since(datetime.datetime.now().timestamp(), self.last_ping.timestamp())))
        log.info('Received a ping. Last ping received {} ago'.format(time_since(datetime.datetime.now().timestamp(), self.last_ping.timestamp())))
        self.last_ping = datetime.datetime.now()

    def on_pong(self, chatconn, event):
        # self.say('Received a pong. Last pong received {} ago'.format(time_since(datetime.datetime.now().timestamp(), self.last_pong.timestamp())))
        log.info('Received a pong. Last pong received {} ago'.format(time_since(datetime.datetime.now().timestamp(), self.last_pong.timestamp())))
        self.last_pong = datetime.datetime.now()

    def on_pubnotice(self, chatconn, event):
        return
        type = 'whisper' if chatconn in self.whisper_manager else 'normal'
        log.debug('NOTICE {}@{}: {}'.format(type, event.target, event.arguments))

    def on_action(self, chatconn, event):
        self.on_pubmsg(chatconn, event)

    def on_pubmsg(self, chatconn, event):
        if event.source.user == self.nickname:
            return False

        # We use .lower() in case twitch ever starts sending non-lowercased usernames
        source = self.users[event.source.user.lower()]

        res = HandlerManager.trigger('on_pubmsg',
                source, event.arguments[0],
                stop_on_false=True)
        if res is False:
            return False

        self.parse_message(event.arguments[0], source, event, tags=event.tags)

    @time_method
    def reload_all(self):
        log.info('Reloading all...')
        for key, manager in self.reloadable.items():
            log.debug('Reloading {0}'.format(key))
            manager.reload()
            log.debug('Done with {0}'.format(key))
        log.info('ok!')

    @time_method
    def commit_all(self):
        log.info('Commiting all...')
        for key, manager in self.commitable.items():
            log.info('Commiting {0}'.format(key))
            manager.commit()
            log.info('Done with {0}'.format(key))
        log.info('ok!')

        HandlerManager.trigger('on_commit', stop_on_false=False)

    def quit(self, message, event, **options):
        quit_chub = self.config['main'].get('control_hub', None)
        quit_delay = 1

        if quit_chub is not None and event.target == ('#{}'.format(quit_chub)):
            quit_delay_random = 300
            try:
                if message is not None and int(message.split()[0]) >= 1:
                    quit_delay_random = int(message.split()[0])
            except (IndexError, ValueError, TypeError):
                pass
            quit_delay = random.randint(0, quit_delay_random)
            log.info('{} is restarting in {} seconds.'.format(self.nickname, quit_delay))

        self.execute_delayed(quit_delay, self.quit_bot)

    def quit_bot(self, **options):
        self.commit_all()
        quit = '{nickname} {version} shutting down...'
        phrase_data = {
                'nickname': self.nickname,
                'version': self.version,
                }

        try:
            self.say(quit.format(**phrase_data))
        except Exception:
            log.exception('Exception caught while trying to say quit phrase')

        self.twitter_manager.quit()
        self.socket_manager.quit()
        self.irc.quit()

        sys.exit(0)

    def apply_filter(self, resp, filter):
        available_filters = {
                'strftime': _filter_strftime,
                'lower': lambda var, args: var.lower(),
                'upper': lambda var, args: var.upper(),
                'time_since_minutes': lambda var, args: 'no time' if var == 0 else time_since(var * 60, 0, format='long'),
                'time_since': lambda var, args: 'no time' if var == 0 else time_since(var, 0, format='long'),
                'time_since_dt': _filter_time_since_dt,
                'urlencode': lambda var, args: urllib.parse.urlencode(var),
                'join': _filter_join,
                'number_format': _filter_number_format,
                }
        if filter.name in available_filters:
            return available_filters[filter.name](resp, filter.arguments)
        return resp

    def find_unique_urls(self, message):
        from pajbot.modules.linkchecker import find_unique_urls
        return find_unique_urls(self.url_regex, message)


def _filter_time_since_dt(var, args):
    try:
        ts = time_since(datetime.datetime.now().timestamp(), var.timestamp())
        if len(ts) > 0:
            return ts
        else:
            return '0 seconds'
    except:
        return 'never FeelsBadMan ?'


def _filter_join(var, args):
    try:
        separator = args[0]
    except IndexError:
        separator = ', '

    return separator.join(var.split(' '))


def _filter_number_format(var, args):
    try:
        return '{0:,d}'.format(int(var))
    except:
        log.exception('asdasd')
    return var


def _filter_strftime(var, args):
    return var.strftime(args[0])
