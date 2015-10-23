import time
import os
import argparse
import sys
import logging
import subprocess

from datetime import datetime

from models.user import UserManager
from models.emote import EmoteManager
from models.setting import Setting
from models.connection import ConnectionManager
from models.whisperconnection import WhisperConnectionManager
from models.linkchecker import LinkChecker
from models.linktracker import LinkTracker
from models.pyramidparser import PyramidParser
from models.websocket import WebSocketManager
from models.twitter import TwitterManager
from scripts.database import update_database

from apiwrappers import TwitchAPI

import pymysql
import wolframalpha

from kvidata import KVIData
from tbmath import TBMath
from pytz import timezone
from tbutil import time_since

import irc.client

from command import Filter
from actions import Action, ActionQueue

log = logging.getLogger('tyggbot')


class TMI:
    message_limit = 90
    whispers_message_limit = 3
    whispers_limit_interval = 3  # in seconds


class TyggBot:
    """
    Main class for the twitch bot
    """

    """ Singleton instance of TyggBot, one instance of the script
    should never have two active classes. """
    instance = None

    version = '1.4.4'
    date_fmt = '%H:%M'
    update_chatters_interval = 5

    default_settings = {
            'broadcaster': 'test_broadcaster',
            'ban_ascii': True,
            'ban_msg_length': True,
            'motd_interval_offline': 60,
            'motd_interval_online': 5,
            'max_msg_length': 350,
            'lines_offline': True,
            'parse_pyramids': False,
            'check_links': True,
            }

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

    def load_default_phrases(self):
        default_phrases = {
                'welcome': False,
                'quit': False,
                'nl': '{username} has typed {num_lines} messages in this channel!',
                'nl_0': '{username} has not typed any messages in this channel BibleThump',
                'nl_pos': '{username} is rank {nl_pos} line-farmer in this channel!',
                'new_sub': 'Sub hype! {username} just subscribed PogChamp',
                'resub': 'Resub hype! {username} just subscribed, {num_months} months in a row PogChamp <3 PogChamp',
                'point_pos': '{username_w_verb} rank {point_pos} point-hoarder in this channel with {points} points.',
                }
        if 'phrases' in self.config:
            self.phrases = {}

            for phrase_key, phrase_value in self.config['phrases'].items():
                log.debug('Including from config {0}: {1}'.format(phrase_key, phrase_value))
                if len(phrase_value.strip()) <= 0:
                    self.phrases[phrase_key] = False
                else:
                    self.phrases[phrase_key] = phrase_value

            for phrase_key, phrase_value in default_phrases.items():
                if phrase_key not in self.phrases:
                    log.debug('Overriding from default {0}: {1}'.format(phrase_key, phrase_value))
                    self.phrases[phrase_key] = phrase_value
        else:
            self.phrases = default_phrases

    def create_sqlconn(self):
        try:
            return pymysql.connect(unix_socket=self.config['sql']['unix_socket'], user=self.config['sql']['user'], passwd=self.config['sql']['passwd'], db=self.config['sql']['db'], charset='utf8mb4')
        except pymysql.err.OperationalError as e:
            error_code, error_message = e.args
            if error_code == 1045:
                log.error('Access denied to database with user \'{0}\'. Review your config file.'.format(self.config['sql']['user']))
            elif error_code == 1044:
                log.error('Access denied to database \'{0}\' with user \'{1}\'. Make sure the database \'{0}\' exists and user \'{1}\' has full access to it.'.format(self.config['sql']['db'], self.config['sql']['user']))
            else:
                log.error(e)

        return None

    def load_config(self, config):
        self.config = config

        if config is None:
            return

        self.nickname = config['main']['nickname']
        self.password = config['main']['password']

        self.default_settings['broadcaster'] = config['main']['streamer']

    def __init__(self, config=None, args=None):
        TyggBot.instance = self

        self.nickname = 'tyggbot'
        self.password = 'abcdef'

        self.load_config(config)

        if config is None:
            return

        self.sqlconn = self.create_sqlconn()
        self.sqlconn.autocommit(True)

        update_database(self.sqlconn)

        self.load_default_phrases()

        self.reactor = irc.client.Reactor()
        self.connection_manager = ConnectionManager(self.reactor, self, TMI.message_limit)

        client_id = None
        oauth = None
        if 'twitchapi' in self.config:
            if 'client_id' in self.config['twitchapi']:
                client_id = self.config['twitchapi']['client_id']
            if 'oauth' in self.config['twitchapi']:
                oauth = self.config['twitchapi']['oauth']

        self.twitchapi = TwitchAPI(client_id, oauth)

        self.reactor.add_global_handler('all_events', self._dispatcher, -10)

        if 'wolfram' in config['main']:
            self.wolfram = wolframalpha.Client(config['main']['wolfram'])
        else:
            self.wolfram = None

        self.whisper_manager = None

        self.is_online = False
        self.ascii_timeout_duration = 120
        self.msg_length_timeout_duration = 120

        self.base_path = os.path.dirname(os.path.realpath(__file__))
        self.data = {}
        self.data_cb = {}

        self.data_cb['status_length'] = self.c_status_length
        self.data_cb['stream_status'] = self.c_stream_status
        self.data_cb['time_norway'] = self.c_time_norway
        self.data_cb['bot_uptime'] = self.c_uptime
        self.data_cb['time_since_latest_deck'] = self.c_time_since_latest_deck
        self.ignores = []

        self.start_time = datetime.now()

        if 'streamer' in config['main']:
            self.streamer = config['main']['streamer']
            self.channel = '#' + self.streamer
        elif 'target' in config['main']:
            self.channel = config['main']['target']
            self.streamer = self.channel[1:]

        if 'control_hub' in config['main']:
            self.control_hub = config['main']['control_hub']
        else:
            self.control_hub = None

        self.kvi = KVIData(self.sqlconn)
        self.tbm = TBMath()
        self.last_sync = time.time()

        self.users = UserManager(self.sqlconn)
        self.emotes = EmoteManager(self.sqlconn)
        self.emotes.load()

        self.silent = False
        self.dev = False

        if 'flags' in config:
            self.silent = True if 'silent' in config['flags'] and config['flags']['silent'] == '1' else self.silent
            self.dev = True if 'dev' in config['flags'] and config['flags']['dev'] == '1' else self.dev

        self.silent = True if args.silent else self.silent

        if self.silent:
            log.info('Silent mode enabled')

        self.reconnection_interval = 5

        # Initialize MOTD-printing
        self.motd_iterator = 0
        self.motd_minute = 0
        self.motd_messages = []
        self.execute_every(60, self.motd_tick)

        self.whisper_manager = WhisperConnectionManager(self.reactor, self, self.streamer, TMI.whispers_message_limit, TMI.whispers_limit_interval)
        self.whisper_manager.start(accounts=[{'username': self.nickname, 'oauth': self.password}])

        self.num_offlines = 0
        self.execute_every(20, self.refresh_stream_status)

        # Actions in this queue are run in a separate thread.
        # This means actions should NOT access any database-related stuff.
        self.action_queue = ActionQueue()
        self.action_queue.start()

        """
        For actions that need to access the main thread,
        we can use the mainthread_queue.
        """
        self.mainthread_queue = ActionQueue()
        self.execute_every(1, self.mainthread_queue.parse_action)

        self.link_checker = LinkChecker(self, self.execute_delayed)
        self.link_tracker = LinkTracker(self.sqlconn)
        self.pyramid_parser = PyramidParser(self)
        self.websocket_manager = WebSocketManager(self)
        self.twitter_manager = TwitterManager(self)

        self.load_all()

        """
        Update chatters every `update_chatters_interval' minutes.
        By default, this is set to run every 5 minutes.
        """
        self.execute_every(self.update_chatters_interval * 60,
                           self.action_queue.add,
                           (self.update_chatters_stage1, ))

        try:
            if self.config['twitchapi']['update_subscribers'] == '1':
                self.execute_every(30 * 60,
                                   self.action_queue.add,
                                   (self.update_subscribers_stage1, ))
        except:
            pass

    def update_subscribers_stage1(self):
        limit = 100
        offset = 0
        subscribers = []

        try:
            subs = self.twitchapi.get_subscribers(self.streamer, limit, offset)
            while len(subs) > 0:
                for sub in subs:
                    subscribers.append(sub['user']['name'])

                offset += limit
                subs = self.twitchapi.get_subscribers(self.streamer, limit, offset)
        except:
            log.exception('Caught an exception while trying to get subscribers')
            return

        if len(subscribers) > 0:
            self.mainthread_queue.add(self.update_subscribers_stage2,
                                      args=[subscribers])

    def update_subscribers_stage2(self, subscribers):
        self.kvi.insert('active_subs', len(subscribers) - 1)

        for username, user in self.users.items():
            if user.subscriber:
                user.subscriber = False
                user.needs_sync = True

        for subscriber in subscribers:
            user = self.users[subscriber]
            user.subscriber = True
            user.needs_sync = True

    def update_chatters_stage1(self):
        chatters = self.twitchapi.get_chatters(self.streamer)
        if len(chatters) > 0:
            self.mainthread_queue.add(self.update_chatters_stage2, args=[chatters])

    def update_chatters_stage2(self, chatters):
        points = 1 if self.is_online else 0

        for chatter in chatters:
            user = self.users[chatter]
            if self.is_online:
                user.minutes_in_chat_online += self.update_chatters_interval
            else:
                user.minutes_in_chat_offline += self.update_chatters_interval
            user.touch(points * (5 if user.subscriber else 1))

    def motd_tick(self):
        if len(self.motd_messages) == 0:
            return

        self.motd_minute += 1
        interval = self.settings['motd_interval_online'] if self.is_online else self.settings['motd_interval_offline']
        if self.motd_minute >= interval:
            self.motd_cycle()

    def motd_cycle(self):
        if len(self.motd_messages) == 0:
            return

        log.debug('Sending MOTD message in the cycle.')
        self.say(self.motd_messages[self.motd_iterator % len(self.motd_messages)])
        self.motd_minute = 0
        self.motd_iterator += 1

    def refresh_stream_status(self):
        try:
            status = self.twitchapi.get_status(self.streamer)
            if status['error'] is True:
                log.error('An error occured while fetching stream status')
                return

            if status['online']:
                self.is_online = True
                self.kvi.set('stream_status', 1)
                self.kvi.set('last_online', int(time.time()))
                self.num_offlines = 0
                self.ascii_timeout_duration = 120
                self.msg_length_timeout_duration = 120
            else:
                self.ascii_timeout_duration = 10
                self.msg_length_timeout_duration = 10
                stream_status = self.kvi.get('stream_status')
                if (stream_status == 1 and self.num_offlines >= 10) or stream_status == 0:
                    self.is_online = False
                    self.kvi.set('stream_status', 0)
                    self.kvi.set('last_offline', int(time.time()))
                else:
                    self.kvi.set('last_online', int(time.time()))
                self.num_offlines += 1
        except:
            log.exception('Uncaught exception while refreshing stream status')

    def _dispatcher(self, connection, event):
        if connection == self.connection_manager.get_main_conn() or connection in self.whisper_manager:
            do_nothing = lambda c, e: None
            method = getattr(self, "on_" + event.type, do_nothing)
            method(connection, event)

    def start(self):
        """Start the IRC client."""
        self.reactor.process_forever()

    def get_kvi_value(self, key, extra={}):
        return self.kvi.get(key)

    def get_last_tweet(self, key, extra={}):
        return self.twitter_manager.get_last_tweet(key)

    def get_emote_tm(self, key, extra={}):
        emote = self.emotes.find(key)
        if emote:
            return emote.tm
        return None

    def get_emote_count(self, key, extra={}):
        emote = self.emotes.find(key)
        if emote:
            return '{0:,d}'.format(emote.count)
        return None

    def get_emote_tm_record(self, key, extra={}):
        emote = self.emotes.find(key)
        if emote:
            return '{0:,d}'.format(emote.tm_record)
        return None

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

    def get_time_value(self, key, extra={}):
        try:
            tz = timezone(key)
            return datetime.now(tz).strftime(self.date_fmt)
        except:
            log.exception('Unhandled exception in get_time_value')

        return None

    def get_value(self, key, extra={}):
        if key in extra:
            return extra[key]
        elif key in self.data:
            return self.data[key]
        elif key in self.data_cb:
            return self.data_cb[key]()
        elif key in self.settings:
            return self.settings[key]

        log.warning('Unknown key passed to get_value: {0}'.format(key))
        return None

    def get_cursor(self):
        self.sqlconn.ping()
        return self.sqlconn.cursor()

    def get_dictcursor(self):
        self.sqlconn.ping()
        return self.sqlconn.cursor(pymysql.cursors.DictCursor)

    def reload(self):
        self.sync_to()
        self.load_all()

    def privmsg(self, message, channel=None):
        try:
            if channel is None:
                channel = self.channel

            self.connection_manager.privmsg(channel, message)
        except Exception:
            log.exception('Exception caught while sending privmsg')

    def c_time_norway(self):
        log.warning('DEPRECATED: use $(time:Europe/Oslo) instead')
        return datetime.now(timezone('Europe/Oslo')).strftime(TyggBot.date_fmt)

    def c_uptime(self):
        return time_since(datetime.now().timestamp(), self.start_time.timestamp())

    def is_online(self):
        return self.kvi.get('stream_status') == 1

    def c_stream_status(self):
        if self.kvi.get('stream_status') == 1:
            return 'online'
        else:
            return 'offline'

    def c_status_length(self):
        stream_status = self.kvi.get('stream_status')

        if stream_status == 1:
            return time_since(time.time(), self.kvi.get('last_offline'))
        else:
            return time_since(time.time(), self.kvi.get('last_online'))

    def c_time_since_latest_deck(self):
        return time_since(time.time(), self.kvi.get('latest_deck_time'))

    def _ban(self, username):
        self.privmsg('.ban {0}'.format(username))

    def execute_at(self, at, function, arguments=()):
        self.reactor.execute_at(at, function, arguments)

    def execute_delayed(self, delay, function, arguments=()):
        self.reactor.execute_delayed(delay, function, arguments)

    def execute_every(self, period, function, arguments=()):
        self.reactor.execute_every(period, function, arguments)

    def ban(self, username):
        self._timeout(username, 30)
        self.execute_delayed(1, self._ban, (username, ))

    def ban_user(self, user):
        if not user.ban_immune:
            self._timeout(user.username, 30)
            self.execute_delayed(1, self._ban, (user.username, ))

    def unban(self, username):
        self.privmsg('.unban {0}'.format(username))

    def _timeout(self, username, duration):
        self.privmsg('.timeout {0} {1}'.format(username, duration))

    def timeout(self, username, duration):
        self._timeout(username, duration)
        self.execute_delayed(1, self._timeout, (username, duration))

    def timeout_user(self, user, duration):
        if not user.ban_immune:
            self._timeout(user.username, duration)
            self.execute_delayed(1, self._timeout, (user.username, duration))

    def whisper(self, username, message):
        if self.whisper_manager:
            self.whisper_manager.whisper(username, message)
        else:
            log.debug('No whisper conn set up.')

    def say(self, message, channel=None):
        if not self.silent:
            message = message.strip()

            if len(message) >= 1:
                if (message[0] == '.' or message[0] == '/') and not message[:3] == '.me':
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

    def sync_to(self):
        self.sqlconn.ping()
        self.sqlconn.autocommit(False)
        cursor = self.sqlconn.cursor()

        log.debug('Syncing data from TyggBot to the database...')

        self.users.sync()

        for trigger, command in self.commands.items():
            if not command.synced:
                command.sync(cursor)
                command.synced = True

        for filter in self.filters:
            if not filter.synced:
                filter.sync(cursor)
                filter.synced = True

        self.emotes.sync()

        self.link_tracker.sync()

        self.sqlconn.commit()
        self.sqlconn.autocommit(True)
        cursor.close()

    def load_all(self):
        self._load_commands()
        self._load_filters()
        self._load_settings()
        self._load_ignores()
        self._load_motd()
        self.twitter_manager.load_relevant_users()

    def _load_commands(self):
        cursor = self.sqlconn.cursor(pymysql.cursors.DictCursor)

        from command import Command

        self.commands = {}

        self.commands['reload'] = Command.admin_command(self.reload)
        self.commands['quit'] = Command.admin_command(self.quit)
        self.commands['ignore'] = Command.dispatch_command('ignore', level=1000)
        self.commands['unignore'] = Command.dispatch_command('unignore', level=1000)
        self.commands['permaban'] = Command.dispatch_command('permaban', level=1000)
        self.commands['unpermaban'] = Command.dispatch_command('unpermaban', level=1000)
        self.commands['twitterfollow'] = Command.dispatch_command('twitter_follow', level=1000)
        self.commands['twitterunfollow'] = Command.dispatch_command('twitter_unfollow', level=1000)
        self.commands['add'] = Command()
        self.commands['add'].load_from_db({
            'id': -1,
            'level': 500,
            'action': '{ "type":"multi", "default":"nothing", "args": [ { "level":500, "command":"banphrase", "action": { "type":"func", "cb":"add_banphrase" } }, { "level":500, "command":"win", "action": { "type":"func", "cb":"add_win" } }, { "level":500, "command":"command", "action": { "type":"func", "cb":"add_command" } }, { "level":2000, "command":"funccommand", "action": { "type":"func", "cb":"add_funccommand" } }, { "level":500, "command":"nothing", "action": { "type":"say", "message":"" } }, { "level":500, "command":"alias", "action": { "type":"func", "cb":"add_alias" } }, { "level":500, "command":"link", "action": { "type":"func", "cb":"add_link" } } ] }',
            'do_sync': False,
            'delay_all': 0,
            'delay_user': 1,
            'extra_args': None,
            })
        self.commands['remove'] = Command()
        self.commands['remove'].load_from_db({
            'id': -1,
            'level': 500,
            'action': '{ "type":"multi", "default":"nothing", "args": [ { "level":500, "command":"banphrase", "action": { "type":"func", "cb":"remove_banphrase" } }, { "level":500, "command":"win", "action": { "type":"func", "cb":"remove_win" } }, { "level":500, "command":"command", "action": { "type":"func", "cb":"remove_command" } }, { "level":500, "command":"nothing", "action": { "type":"say", "message":"" } }, { "level":500, "command":"alias", "action": { "type":"func", "cb":"remove_alias" } }, { "level":500, "command":"link", "action": { "type":"func", "cb":"remove_link" } } ] }',
            'do_sync': False,
            'delay_all': 0,
            'delay_user': 1,
            'extra_args': None,
            })
        self.commands['rem'] = self.commands['remove']
        self.commands['del'] = self.commands['remove']
        self.commands['delete'] = self.commands['remove']
        self.commands['debug'] = Command()
        self.commands['debug'].load_from_db({
            'id': -1,
            'level': 250,
            'action': '{ "type":"multi", "default":"nothing", "args": [ { "level":250, "command":"command", "action": { "type":"func", "cb":"debug_command" } }, { "level":250, "command":"user", "action": { "type":"func", "cb":"debug_user" } }, { "level":250, "command":"nothing", "action": { "type":"say", "message":"" } } ] }',
            'do_sync': False,
            'delay_all': 0,
            'delay_user': 1,
            'extra_args': None,
            })
        self.commands['level'] = Command.dispatch_command('level', 1000)
        self.commands['eval'] = Command.dispatch_command('eval', 2000)

        num_commands = 0
        num_aliases = 0

        cursor.execute('SELECT * FROM `tb_commands`')

        for row in cursor:
            try:
                cmd = Command()
                cmd.load_from_db(row)

                if cmd.is_enabled():
                    num_commands += 1
                    for alias in row['command'].split('|'):
                        if alias not in self.commands:
                            self.commands[alias] = cmd
                            num_aliases += 1
                        else:
                            log.error('Command !{0} is already in use'.format(alias))
            except Exception:
                log.exception('Exception caught when loading command')
                continue

        log.info(num_commands)
        log.info(num_aliases)
        num_aliases -= num_commands

        log.debug('Loaded {0} commands ({1} additional aliases)'.format(num_commands, num_aliases))
        cursor.close()

    def _load_filters(self):
        cursor = self.sqlconn.cursor(pymysql.cursors.DictCursor)

        cursor.execute('SELECT * FROM `tb_filters`')

        self.filters = []

        num_filters = 0

        for row in cursor:
            try:
                filter = Filter(row)

                if filter.is_enabled():
                    self.filters.append(filter)
                    num_filters += 1
            except Exception:
                log.exception('Exception caught when loading filter')
                continue

        log.debug('Loaded {0} filters'.format(num_filters))
        cursor.close()

    def _load_settings(self):
        cursor = self.sqlconn.cursor(pymysql.cursors.DictCursor)

        cursor.execute('SELECT * FROM `tb_settings`')

        self.settings = {}

        for row in cursor:
            self.settings[row['setting']] = Setting.parse(row['type'], row['value'])
            if self.settings[row['setting']] is None:
                log.error('ERROR LOADING SETTING {0}'.format(row['setting']))

        for setting in self.default_settings:
            if setting not in self.settings:
                self.settings[setting] = self.default_settings[setting]

        cursor.close()

        if self.dev:
            try:
                current_branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode('utf8').strip()
                latest_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf8').strip()[:8]
                commit_number = subprocess.check_output(['git', 'rev-list', 'HEAD', '--count']).decode('utf8').strip()
                self.version = '{0} DEV ({1}, {2}, commit {3}, db version {4})'.format(self.version, current_branch, latest_commit, commit_number, self.settings['db_version'])
                log.info(current_branch)
            except:
                log.exception('what')

    def _load_ignores(self):
        cursor = self.sqlconn.cursor(pymysql.cursors.DictCursor)

        cursor.execute('SELECT * FROM `tb_ignores`')

        self.ignores = []

        for row in cursor:
            self.ignores.append(row['username'])

        cursor.close()

    def _load_motd(self):
        cursor = self.sqlconn.cursor(pymysql.cursors.DictCursor)

        cursor.execute('SELECT * FROM `tb_motd` WHERE `enabled`=1')

        self.motd_messages = []

        for row in cursor:
            self.motd_messages.append(row['message'])

        cursor.close()

    def on_welcome(self, chatconn, event):
        if chatconn in self.whisper_manager:
            log.debug('Connected to Whisper server.')
        else:
            log.debug('Connected to IRC server.')

    def connect(self):
        return self.connection_manager.start()

    def on_disconnect(self, chatconn, event):
        if chatconn in self.whisper_manager:
            log.debug('Disconnecting from Whisper server')
            self.whisper_manager.on_disconnect(chatconn)

        else:
            log.debug('Disconnected from IRC server')
            self.connection_manager.on_disconnect(chatconn)

    def check_msg_content(self, source, msg_raw, event):
        msg_lower = msg_raw.lower()

        for f in self.filters:
            if f.type == 'regex':
                m = f.search(source, msg_lower)
                if m:
                    log.debug('Matched regex filter \'{0}\''.format(f.name))
                    f.run(self, source, msg_raw, event, {'match': m})
                    return True
            elif f.type == 'banphrase':
                if f.filter in msg_lower:
                    log.debug('Matched banphrase filter \'{0}\''.format(f.name))
                    f.run(self, source, msg_raw, event)
                    return True
        return False  # message was ok

    def parse_message(self, msg_raw, source, event, tags={}, whisper=False):
        msg_lower = msg_raw.lower()

        if source is None:
            log.error('No valid user passed to parse_message')
            return False

        if source.banned:
            self.ban(source.username)
            return False

        for tag in tags:
            if tag['key'] == 'subscriber':
                if source.subscriber and tag['value'] == '0':
                    source.subscriber = False
                    source.needs_sync = True
                elif not source.subscriber and tag['value'] == '1':
                    source.subscriber = True
                    source.needs_sync = True
            elif tag['key'] == 'emotes' and tag['value']:
                emote_data = tag['value'].split('/')
                for emote in emote_data:
                    try:
                        emote_id, emote_occurrence = emote.split(':')
                        emote_indices = emote_occurrence.split(',')
                        emote_count = len(emote_indices)
                        emote = self.emotes[int(emote_id)]
                        emote.add(emote_count, self.reactor)
                        if emote.id == -1 and emote.code is None:
                            # The emote we just detected is new, set its code.
                            first_index, last_index = emote_indices[0].split('-')
                            emote.code = msg_raw[int(first_index):int(last_index) + 1]
                            if emote.code not in self.emotes:
                                self.emotes[emote.code] = emote
                    except:
                        log.exception('Exception caught while splitting emote data')
            elif tag['key'] == 'display-name' and tag['value']:
                try:
                    source.update_username(tag['value'])
                except:
                    log.exception('Exception caught while updating a users username')

        if self.settings['parse_pyramids'] and whisper is False:
            self.pyramid_parser.parse_line(msg_raw, source)

        for emote in self.emotes.custom_data:
            num = len(emote.regex.findall(msg_raw))
            if num > 0:
                emote.add(num, self.reactor)

        log.debug('{2}{0}: {1}'.format(source.username, msg_raw, '<w>' if whisper else ''))

        if not whisper:
            if source.level < 500:
                if self.check_msg_content(source, msg_raw, event):
                    # If we've matched a filter, we should not have to run a command.
                    return

            urls = self.link_checker.find_urls_in_message(msg_raw)
            for url in urls:
                self.link_tracker.add(url)

                if self.settings['check_links']:
                    if source.level < 500:
                        # Action which will be taken when a bad link is found
                        action = Action(self.timeout, args=[source.username, 20])
                        # Queue up a check on the URL
                        self.action_queue.add(self.link_checker.check_url, args=[url, action])

        if source.ignored:
            return False

        add_line = not whisper and (self.is_online or self.settings['lines_offline'])

        if msg_lower[:1] == '!':
            msg_lower_parts = msg_lower.split(' ')
            trigger = msg_lower_parts[0][1:]
            msg_raw_parts = msg_raw.split(' ')
            remaining_message = ' '.join(msg_raw_parts[1:]) if len(msg_raw_parts) > 1 else None
            if trigger in self.commands:
                command = self.commands[trigger]
                command.run(self, source, remaining_message, event=event, whisper=whisper)
                # If a command is executed, we do not count the message as a line
                add_line = False

        source.wrote_message(add_line)

    def on_whisper(self, chatconn, event):
        # We use .lower() in case twitch ever starts sending non-lowercased usernames
        source = self.users[event.source.user.lower()]
        self.parse_message(event.arguments[0], source, event, whisper=True)

    def on_action(self, chatconn, event):
        self.on_pubmsg(chatconn, event)

    def on_pubmsg(self, chatconn, event):
        if event.source.user == self.nickname:
            return False

        # We use .lower() in case twitch ever starts sending non-lowercased usernames
        source = self.users[event.source.user.lower()]

        cur_time = time.time()

        msg = event.arguments[0]
        msg_len = len(msg)

        if msg_len > 70 and source.level < 500:
            non_alnum = sum(not c.isalnum() for c in msg)
            ratio = non_alnum / msg_len

            # TODO: Implement a better anti-ascii feature.
            if self.settings['ban_ascii']:
                if (msg_len > 240 and ratio > 0.8) or ratio > 0.93:
                    log.debug('Timeouting {0} because of a high ascii ratio ({1}). Message length: {2}'.format(source.username, ratio, msg_len))
                    self.timeout_user(source, self.ascii_timeout_duration)
                    self.whisper(source.username, 'You have been timed out for {0} seconds because your message contained too many ascii characters.'.format(self.ascii_timeout_duration))
                    return

            if self.settings['ban_msg_length']:
                max_msg_length = self.settings['max_msg_length']
                if msg_len > max_msg_length:
                    log.debug('Timeouting {0} because of a message length: {1}'.format(source.username, msg_len))
                    self.timeout_user(source, self.msg_length_timeout_duration)
                    self.whisper(source.username, 'You have been timed out for {0} seconds because your message was too long.'.format(self.msg_length_timeout_duration))
                    return

        if cur_time - self.last_sync >= 10 * 60:
            self.sync_to()
            self.last_sync = cur_time

        self.parse_message(event.arguments[0], source, event, tags=event.tags)

    def quit(self):
        self.sync_to()
        if self.phrases['quit']:
            phrase_data = {
                    'nickname': self.nickname,
                    'version': self.version,
                    }

            try:
                self.say(self.phrases['quit'].format(**phrase_data))
            except Exception:
                log.exception('Exception caught while trying to say quit phrase')

        self.twitter_manager.quit()

        if self.whisper_manager:
            self.whisper_manager.quit()

        sys.exit(0)
