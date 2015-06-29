import json, time, os, argparse, re, sys, logging, math, random
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import datetime as dt
import collections

from models.user import User, UserManager

import pymysql
import wolframalpha
import tweepy

from dispatch import Dispatch
from kvidata import KVIData
from tbmath import TBMath
from pytz import timezone
from whisperconn import WhisperConn
from tbutil import SyncValue, time_since

import irc.client

from command import Filter, Command

log = logging.getLogger('tyggbot')

class TMI:
    message_limit = 50

class Emote:
    def __init__(self, code):
        self.code = code
        self.pm = 0
        self.tm = 0
        self.count = 0
        self.regex = re.compile('(?<![\w]){0}(?![\w])'.format(code))
        self.deque = collections.deque([0]*61)

    def add(self, count):
        self.count += count
        self.deque[0] += count
        self.tm += count

    # Shift the deque and recalculate all relevant values
    def shift(self):
        cur_sum = sum(self.deque)
        self.pm = cur_sum / 60
        self.tm = cur_sum
        self.deque.rotate(1)
        self.deque[60] = 0

class TyggBot:
    """
    Main class for the twitch bot
    """

    version = '0.9.1'
    date_fmt = '%H:%M'
    #date_fmt = '%A %B '
    commands = {}
    filters = []
    settings = {}
    emotes = {}
    emote_stats = {}

    silent = False
    dev = False

    """ Singleton instance of TyggBot, one instance of the script
    should never have two active classes."""
    instance = None

    def parse_args():
        parser = argparse.ArgumentParser()
        parser.add_argument('action', choices=('start', 'stop', 'restart', 'normal'), nargs='?')
        parser.add_argument('--silent',
                action='count',
                help='Decides whether the bot should be silent or not')
        # TODO: Add a log level argument.

        return parser.parse_args()

    def init_twitter(self):
        try:
            auth = tweepy.OAuthHandler(self.config['twitter']['consumer_key'], self.config['twitter']['consumer_secret'])
            auth.set_access_token(self.config['twitter']['access_token'], self.config['twitter']['access_token_secret'])

            self.twitter = tweepy.API(auth)
        except:
            log.error('Twitter authentication failed.')
            self.twitter = False

    def __init__(self, config, args):
        self.reactor = irc.client.Reactor()
        self.connection = self.reactor.server()

        self.reactor.add_global_handler('all_events', self._dispatcher, -10)

        if 'wolfram' in config['main']:
            Dispatch.wolfram = wolframalpha.Client(config['main']['wolfram'])
        else:
            wolfram = None

        self.sched = BackgroundScheduler()
        self.sched.start()

        self.whisper_conn = None

        TyggBot.instance = self

        self.base_path = os.path.dirname(os.path.realpath(__file__))
        self.data = {}
        self.data_cb = {}

        self.data_cb['status_length'] = self.c_status_length
        self.data_cb['stream_status'] = self.c_stream_status
        self.data_cb['time_norway'] = self.c_time_norway
        self.data_cb['bot_uptime'] = self.c_uptime
        self.ignores = []

        self.start_time = datetime.now()


        self.config = config
        self.target = config['main']['target']
        self.sqlconn = pymysql.connect(unix_socket=config['sql']['unix_socket'], user=config['sql']['user'], passwd=config['sql']['passwd'], db=config['sql']['db'], charset='utf8')
        self.sqlconn.autocommit(True)
        self.kvi = KVIData(self.sqlconn)
        self.tbm = TBMath()
        self.last_sync = time.time()

        self.users = UserManager(self.sqlconn)

        if 'flags' in config:
            self.silent = True if 'silent' in config['flags'] and config['flags']['silent'] == '1' else self.silent
            self.dev = True if 'dev' in config['flags'] and config['flags']['dev'] == '1' else self.dev

        self.silent = True if args.silent else self.silent

        if self.silent:
            log.info('Silent mode enabled')

        self.sync_from()

        self.server = config['main']['server']
        self.port = int(config['main']['port'])
        self.nickname = config['main']['nickname']
        self.password = config['main']['password']
        self.reconnection_interval = 5

        self.load_all()

        self.whisper_conn = WhisperConn(self.target[1:], self.nickname, self.password, self.reactor)
        self.whisper_conn.connect()

        banned_characters = '͖͈̞̩͎̻̫̫̜͉̠̫͕̭̭̫̫̹̗̹͈̼̠̖͍͚̥͈̮̼͕̠̤̻ด้็็็็็้็็็็็้็็็็็้็็็็็้็็็็็้็็็็็้็็็็็้็็็็็'
        self.banned_chars = [x for x in banned_characters]

        self.num_commands_sent = 0
        self.connection.execute_every(30, self.reset_command_throttle)

        if 'twitter' in config:
            self.init_twitter()
        else:
            self.twitter = None

        self.emotes = [
                Emote('Kappa'),
                Emote('PogChamp'),
                Emote('BabyRage'),
                Emote('OpieOP'),
                Emote('KaRappa'),
                Emote('4Head'),
            ]

        self.connection.execute_every(1, self.shift_emotes)

    def shift_emotes(self):
        for emote in self.emotes:
            emote.shift()

    def reset_command_throttle(self):
        self.num_commands_sent = 0

    def _dispatcher(self, connection, event):
        do_nothing = lambda c, e: None
        method = getattr(self, "on_" + event.type, do_nothing)
        method(connection, event)

    def start(self):
        """Start the IRC client."""
        self.reactor.process_forever()

    def get_kvi_value(self, key, extra={}):
        return self.kvi.get(key)

    def get_last_tweet(self, key, extra={}):
        if self.twitter:
            try:
                public_tweets = self.twitter.user_timeline(key)
                for tweet in public_tweets:
                    if not tweet.text.startswith('RT ') and tweet.in_reply_to_screen_name is None:
                        log.info(tweet.created_at)
                        log.info(datetime.now())
                        return '{0} ({1} ago)'.format(tweet.text, time_since(datetime.now().timestamp(), tweet.created_at.timestamp(), format='short'))
            except Exception as e:
                log.error('Exception caught {0}'.format(e))
                return 'FeelsBadMan'
        else:
            return 'Twitter not set up FeelsBadMan'

        return 'FeelsBadMan'

    def get_emote_pm(self, key, extra={}):
        for emote in self.emotes:
            if key == emote.code:
                return emote.pm
        return 0

    def get_emote_tm(self, key, extra={}):
        for emote in self.emotes:
            if key == emote.code:
                return emote.ttm
        return 0

    def get_emote_count(self, key, extra={}):
        for emote in self.emotes:
            if key == emote.code:
                return emote.count
        return 0

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
        return '???'

    def get_cursor(self):
        self.sqlconn.ping()
        return self.sqlconn.cursor()

    def get_dictcursor(self):
        self.sqlconn.ping()
        return self.sqlconn.cursor(pymysql.cursors.DictCursor)

    def reload(self):
        self.sync_to()
        self.load_all()

    def privmsg(self, target, message, priority=False):
        # Non-prioritized messages are allowed 50% of the message limit
        if (not priority and self.num_commands_sent > TMI.message_limit/2) or (priority and self.num_commands_sent > TMI.message_limit):
            log.error('Skipping this say, because we are sending too many messages.')
            return False

        try:
            if not target:
                target = self.target

            self.connection.privmsg(target, message)
            self.num_commands_sent += 1
        except Exception as e:
            log.error('Exception caught while sending privmsg: {0}'.format(e))

    def c_time_norway(self):
        return datetime.now(timezone('Europe/Oslo')).strftime(TyggBot.date_fmt)

    def c_uptime(self):
        return time_since(datetime.now().timestamp(), self.start_time.timestamp())

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

    def run_later(self, job_fn, *fn_args, **delta_args):
        time = datetime.now() + dt.timedelta(**delta_args)
        return self.sched.add_job(job_fn, 'date', args=fn_args, run_date=time)

    def _ban(self, username, target=None):
        self.privmsg(target, '.ban {0}'.format(username), True)

    def ban(self, username, target=None):
        self._timeout(username, 30, target)
        self.run_later(self._ban, username, 1, target, seconds=1)

    def unban(self, username, target=None):
        self.privmsg(target, '.unban {0}'.format(username), True)

    def _timeout(self, username, duration, target=None):
        self.privmsg(target, '.timeout {0} {1}'.format(username, duration), True)

    def timeout(self, username, duration, target=None):
        self._timeout(username, duration, target)
        self.run_later(self._timeout, username, duration, target, seconds=1)

    def whisper(self, username, message):
        if self.whisper_conn:
            log.debug('Sending whisper {0} to {1}'.format(message, username))
            self.whisper_conn.whisper(username, message)
        else:
            log.debug('No whisper conn set up.')

    def say(self, message, target=None, force=False):
        if force or not self.silent:
            message = message.strip()

            if len(message) >= 1:
                if message[0] == '.' or message[0] == '/':
                    log.warning('Message we attempted to send started with . or /, skipping.')
                    return

                log.info('Sending message: {0}'.format(message))

                self.privmsg(target, message[:400])
            else:
                log.warning('Message too short, skipping...')

    def me(self, message, target=None, force=False):
        if force or not self.silent:
            message = message.strip()

            if len(message) >= 1:
                if message[0] == '.' or message[0] == '/':
                    log.warning('Message we attempted to send started with . or /, skipping.')
                    return

                log.info('Sending message: {0}'.format(message))

                self.privmsg(target, '.me ' + message[:400])
            else:
                log.warning('Message too short, skipping...')

    def sync_to(self):
        if self.dev:
            log.debug('Dev mode is enabled, not syncing data.')
            return

        self.sqlconn.ping()
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

        for emote, value in self.emote_stats.items():
            if not value.synced:
                cursor.execute('INSERT INTO `tb_idata` (`id`, value, type) VALUES(%s, %s, "emote_stats") ON DUPLICATE KEY UPDATE value=%s',
                        (emote, value.value, value.value))
                value.synced = True

        cursor.close()

    def sync_from(self):
        for nl in self.kvi.fetch_all('emote_stats'):
            self.emote_stats[nl['key']] = SyncValue(nl['value'], True)

    def load_all(self):
        self._load_commands()
        self._load_filters()
        self._load_settings()
        self._load_ignores()

    def _load_commands(self):
        cursor = self.sqlconn.cursor(pymysql.cursors.DictCursor)

        from command import Command

        cursor.execute('SELECT * FROM `tb_commands`')

        self.commands = {}

        self.commands['reload'] = Command.admin_command(self.reload)
        self.commands['quit'] = Command.admin_command(self.quit)
        self.commands['ignore'] = Command.admin_command(Dispatch.ignore, type='func')
        self.commands['unignore'] = Command.admin_command(Dispatch.unignore, type='func')
        self.commands['add'] = Command()
        self.commands['add'].load_from_db({
            'id': -1,
            'level': 500,
            'action': '{ "type":"multi", "default":"nothing", "args": [ { "level":500, "command":"banphrase", "action": { "type":"func", "cb":"add_banphrase" } }, { "level":500, "command":"win", "action": { "type":"func", "cb":"add_win" } }, { "level":500, "command":"command", "action": { "type":"func", "cb":"add_command" } }, { "level":500, "command":"nothing", "action": { "type":"say", "message":"" } } ] }',
            'do_sync': False,
            'delay_all': 5,
            'delay_user': 15,
            'enabled': True,
            'num_uses': 0,
            'extra_args': None,
            })
        self.commands['remove'] = Command()
        self.commands['remove'].load_from_db({
            'id': -1,
            'level': 500,
            'action': '{ "type":"multi", "default":"nothing", "args": [ { "level":500, "command":"banphrase", "action": { "type":"func", "cb":"remove_banphrase" } }, { "level":500, "command":"win", "action": { "type":"func", "cb":"remove_win" } }, { "level":500, "command":"command", "action": { "type":"func", "cb":"remove_command" } }, { "level":500, "command":"nothing", "action": { "type":"say", "message":"" } } ] }',
            'do_sync': False,
            'delay_all': 5,
            'delay_user': 15,
            'enabled': True,
            'num_uses': 0,
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
            'delay_all': 5,
            'delay_user': 15,
            'enabled': True,
            'num_uses': 0,
            'extra_args': None,
            })
        self.commands['level'] = Command.admin_command(Dispatch.level, type='func')

        num_commands = 0
        num_aliases = 0

        for row in cursor:
            try:
                cmd = Command()
                cmd.load_from_db(row)

                if cmd.is_enabled():
                    for alias in row['command'].split('|'):
                        if alias not in self.commands:
                            self.commands[alias] = cmd
                            num_aliases += 1
                        else:
                            log.error('Command !{0} is already in use'.format(alias))

                num_commands += 1
            except Exception as e:
                log.error('Exception caught when loading command: {0}'.format(e))
                continue

        log.debug('Loaded {0} commands ({1} aliases)'.format(num_commands, num_aliases))
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
            except Exception as e:
                log.error('Exception caught when loading filter: {0}'.format(e))
                continue

        log.debug('Loaded {0} filters'.format(num_filters))
        cursor.close()

    def _load_settings(self):
        cursor = self.sqlconn.cursor(pymysql.cursors.DictCursor)

        cursor.execute('SELECT * FROM `tb_settings`')

        self.settings = {}

        for row in cursor:
            try:
                if row['type'] == 'int':
                    self.settings[row['setting']] = int(row['value'])
                elif row['type'] == 'string':
                    self.settings[row['setting']] = row['value']
                elif row['type'] == 'list':
                    self.settings[row['setting']] = row['value'].split(',')
                else:
                    log.error('Invalid setting type: {0}'.format(row['type']))
            except Exception as e:
                log.error('Exception caught when loading setting: {0}'.format(e))
                continue

        cursor.close()

    def _load_ignores(self):
        cursor = self.sqlconn.cursor(pymysql.cursors.DictCursor)

        cursor.execute('SELECT * FROM `tb_ignores`')

        self.ignores = []

        for row in cursor:
            self.ignores.append(row['username'])

        cursor.close()

    def on_welcome(self, chatconn, event):
        if chatconn == self.connection:
            log.debug('Connected to IRC server.')
            if irc.client.is_channel(self.target):
                chatconn.join(self.target)

                try:
                    if 'phrases' in self.config and 'welcome' in self.config['phrases']:
                        self.say(self.config['phrases']['welcome'].format(self))
                except Exception as e:
                    log.error(e)
        elif chatconn == self.whisper_conn:
            log.debug('Connected to Whisper server.')

    def _connected_checker(self):
        if not self.connection.is_connected():
            self.connection.execute_delayed(self.reconnection_interval,
                                            self._connected_checker)

            self.connect()

    def connect(self):
        log.debug('Connecting to IRC server...')
        try:
            irc.client.SimpleIRCClient.connect(self, self.server, self.port, self.nickname, self.password, self.nickname)
        except irc.client.ServerConnectionError:
            pass

    def on_disconnect(self, chatconn, event):
        if chatconn == self.connection:
            log.debug('Disconnected from IRC server')
            self.sync_to()
            self.connection.execute_delayed(self.reconnection_interval,
                                            self._connected_checker)
        elif chatconn == self.whisper_conn:
            log.debug('Disconnecting from Whisper server')
            self.whisper_conn.execute_delayed(self.whisper_conn.reconnection_interval,
                                              self.whisper_conn._connected_checker)

    def parse_message(self, msg_raw, source=None, event=None, pretend=False, force=False):
        msg_lower = msg_raw.lower()

        for emote in self.emotes:
            num = len(emote.regex.findall(msg_raw))
            if num > 0:
                emote.add(num)

        if source is None and not event:
            log.error('No nick or event passed to parse_message')
            return False

        for b in self.banned_chars:
            if b in msg_raw:
                self.timeout(source.username, 120)
                return

        log.debug('{0}: {1}'.format(source.username, msg_raw))

        if 'emotes' in self.settings:
            for emote in self.settings['emotes']:
                if emote in msg_raw:
                    if emote not in self.emote_stats:
                        self.emote_stats[emote] = SyncValue(1)
                    else:
                        self.emote_stats[emote].increment()

        if not force:
            if source.level < 500:
                for f in self.filters:
                    if f.type == 'regex':
                        m = f.search(source, msg_lower)
                        if m:
                            log.debug('Matched regex filter \'{0}\''.format(f.name))
                            f.run(self, source, msg_raw, event, {'match':m})
                            # If we've matched a filter, we should not have to run a command.
                            return
                    elif f.type == 'banphrase':
                        if f.filter in msg_lower:
                            log.debug('Matched banphrase filter \'{0}\''.format(f.name))
                            f.run(self, source, msg_raw, event)
                            # If we've matched a filter, we should not have to run a command.
                            return

            # TODO: Change to if source.ignored
            if source.username in self.ignores:
                return

        if msg_lower[:1] == '!':
            msg_lower_parts = msg_lower.split(' ')
            command = msg_lower_parts[0][1:]
            msg_raw_parts = msg_raw.split(' ')
            extra_msg = ' '.join(msg_raw_parts[1:]) if len(msg_raw_parts) > 1 else None
            if command in self.commands:
                if source.level >= self.commands[command].level:
                    self.commands[command].run(self, source, extra_msg, event)
                    return

        source.num_lines += 1
        source.needs_sync = True

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

        if msg_len > 70:
            non_alnum = sum(not c.isalnum() for c in msg)
            ratio = non_alnum/msg_len

            log.debug('Ascii ratio: {0}'.format(ratio))
            if (msg_len > 140 and ratio > 0.8) or ratio > 0.91:
                log.debug('Timeouting {0} because of a high ascii ratio ({1}). Message length: {2}'.format(source.username, ratio, msg_len))
                self.timeout(source.username, 120)
                return

            if msg_len > 450:
                log.debug('Timeouting {0} because of a message length: {1}'.format(source.username, msg_len))
                self.timeout(source.username, 20)
                self.me('{0}, you have been timed out because your message was too long.'.format(source.nick))
                return

        if cur_time - self.last_sync >= 60:
            self.sync_to()
            self.last_sync = cur_time

        self.parse_message(event.arguments[0], source, event)

    def quit(self):
        self.sync_to()
        try:
            if 'phrases' in self.config and 'quit' in self.config['phrases']:
                self.say(self.config['phrases']['quit'].format(self))
        except Exception as e:
            log.error(e)

        self.connection.quit("bye")

#from tbactions import TBAction, FuncAction, RawFuncAction, SayAction
