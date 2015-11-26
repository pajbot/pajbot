import time
import argparse
import sys
import logging
import subprocess

from datetime import datetime

from .models.user import UserManager
from .models.emote import EmoteManager
from .models.connection import ConnectionManager
from .models.whisperconnection import WhisperConnectionManager
from .models.linkchecker import LinkChecker
from .models.linktracker import LinkTracker
from .models.pyramidparser import PyramidParser
from .models.websocket import WebSocketManager
from .models.twitter import TwitterManager
from .models.db import DBManager
from .models.filter import FilterManager
from .models.command import CommandManager
from .models.setting import SettingManager
from .models.motd import MOTDManager
from .models.kvi import KVIManager
from .models.deck import DeckManager
from .models.stream import StreamManager
from .models.webcontent import WebContent
from .models.time import TimeManager
from .apiwrappers import TwitchAPI
from .tbmath import TBMath
from .tbutil import time_since
from .tbutil import time_method
from .actions import Action, ActionQueue

import wolframalpha
from pytz import timezone
import irc.client


log = logging.getLogger('tyggbot')


class TMI:
    message_limit = 90
    whispers_message_limit = 20
    whispers_limit_interval = 5  # in seconds


class TyggBot:
    """
    Main class for the twitch bot
    """

    """ Singleton instance of TyggBot, one instance of the script
    should never have two active classes. """
    instance = None

    version = '2.0.4'
    date_fmt = '%H:%M'
    update_chatters_interval = 5
    admin = None

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
                if len(phrase_value.strip()) <= 0:
                    self.phrases[phrase_key] = False
                else:
                    self.phrases[phrase_key] = phrase_value

            for phrase_key, phrase_value in default_phrases.items():
                if phrase_key not in self.phrases:
                    self.phrases[phrase_key] = phrase_value
        else:
            self.phrases = default_phrases

    def load_config(self, config):
        self.config = config

        self.nickname = config['main'].get('nickname', 'tyggbot')
        self.password = config['main'].get('password', 'abcdef')

        self.timezone = config['main'].get('timezone', 'UTC')

        TimeManager.init_timezone(self.timezone)

        if 'streamer' in config['main']:
            self.streamer = config['main']['streamer']
            self.channel = '#' + self.streamer
        elif 'target' in config['main']:
            self.channel = config['main']['target']
            self.streamer = self.channel[1:]

        if 'wolfram' in config['main']:
            self.wolfram = wolframalpha.Client(config['main']['wolfram'])
        else:
            self.wolfram = None

        self.silent = False
        self.dev = False

        if 'flags' in config:
            self.silent = True if 'silent' in config['flags'] and config['flags']['silent'] == '1' else self.silent
            self.dev = True if 'dev' in config['flags'] and config['flags']['dev'] == '1' else self.dev

        DBManager.init(self.config['main']['db'])

    def __init__(self, config, args=None):
        TyggBot.instance = self

        self.load_config(config)

        self.load_default_phrases()

        self.db_session = DBManager.create_session()

        try:
            subprocess.check_call(['alembic', 'upgrade', 'head'] + ['--tag="{0}"'.format(' '.join(sys.argv[1:]))])
        except subprocess.CalledProcessError:
            log.exception('aaaa')
            log.error('Unable to call `alembic upgrade head`, this means the database could be out of date. Quitting.')
            sys.exit(1)
        except FileNotFoundError:
            log.error('Could not found an installation of alembic. Please install alembic to continue.')
            sys.exit(1)
        except:
            log.exception('Unhandled exception when calling db update')
            sys.exit(1)

        self.reactor = irc.client.Reactor()
        self.start_time = datetime.now()

        self.users = UserManager()
        self.decks = DeckManager().reload()
        self.commands = CommandManager().reload()
        self.filters = FilterManager().reload()
        self.settings = SettingManager({'broadcaster': self.streamer}).reload()
        self.motd_manager = MOTDManager(self).reload()
        self.kvi = KVIManager().reload()
        self.emotes = EmoteManager().reload()
        self.link_tracker = LinkTracker()
        self.link_checker = LinkChecker(self, self.execute_delayed).reload()
        self.twitter_manager = TwitterManager(self).reload()
        self.stream_manager = StreamManager(self)

        # Reloadable managers
        self.reloadable = {
                'commands': self.commands,
                'filters': self.filters,
                'settings': self.settings,
                'motd': self.motd_manager,
                'kvi': self.kvi,
                'emotes': self.emotes,
                'twitter': self.twitter_manager,
                'linkchecker': self.link_checker,
                'decks': self.decks,
                }

        # Commitable managers
        self.commitable = {
                'commands': self.commands,
                'filters': self.filters,
                'settings': self.settings,
                'motd': self.motd_manager,
                'kvi': self.kvi,
                'emotes': self.emotes,
                'twitter': self.twitter_manager,
                'linkchecker': self.link_checker,
                'decks': self.decks,
                'linktracker': self.link_tracker,
                'users': self.users,
                }

        self.execute_every(10 * 60, self.commit_all)

        try:
            self.admin = self.config['main']['admin']
        except KeyError:
            log.warning('No admin user specified. See the [main] section in config.example.ini for its usage.')
        if self.admin:
            self.users[self.admin].level = 2000

        self.parse_version()

        self.connection_manager = ConnectionManager(self.reactor, self, TMI.message_limit, streamer=self.streamer)
        chub = self.config['main'].get('control_hub', None)
        if chub is not None:
            self.control_hub = ConnectionManager(self.reactor, self, TMI.message_limit, streamer=chub, backup_conns=1)
            log.info('start pls')
        else:
            self.control_hub = None

        twitch_client_id = None
        twitch_oauth = None
        if 'twitchapi' in self.config:
            twitch_client_id = self.config['twitchapi'].get('client_id', None)
            twitch_oauth = self.config['twitchapi'].get('oauth', None)

        self.twitchapi = TwitchAPI(twitch_client_id, twitch_oauth)

        self.reactor.add_global_handler('all_events', self._dispatcher, -10)

        self.whisper_manager = WhisperConnectionManager(self.reactor, self, self.streamer, TMI.whispers_message_limit, TMI.whispers_limit_interval)
        self.whisper_manager.start(accounts=[{'username': self.nickname, 'oauth': self.password, 'can_send_whispers': self.config.getboolean('main', 'add_self_as_whisper_account')}])

        self.ascii_timeout_duration = 120
        self.msg_length_timeout_duration = 120

        self.data = {}
        self.data_cb = {}

        self.data_cb['status_length'] = self.c_status_length
        self.data_cb['stream_status'] = self.c_stream_status
        self.data_cb['time_norway'] = self.c_time_norway
        self.data_cb['bot_uptime'] = self.c_uptime
        self.data_cb['time_since_latest_deck'] = self.c_time_since_latest_deck

        self.tbm = TBMath()

        self.silent = True if args.silent else self.silent

        if self.silent:
            log.info('Silent mode enabled')

        self.reconnection_interval = 5

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

        self.pyramid_parser = PyramidParser(self)
        self.websocket_manager = WebSocketManager(self)

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

    def update_chatters_stage1(self):
        chatters = self.twitchapi.get_chatters(self.streamer)
        if len(chatters) > 0:
            self.mainthread_queue.add(self.update_chatters_stage2, args=[chatters])

    def update_chatters_stage2(self, chatters):
        points = 1 if self.is_online else 0

        log.debug('Updating {0} chatters'.format(len(chatters)))

        u_chatters = self.users.bulk_load(chatters)

        for user in u_chatters:
            if self.is_online:
                user.minutes_in_chat_online += self.update_chatters_interval
            else:
                user.minutes_in_chat_offline += self.update_chatters_interval
            num_points = points * (5 if user.subscriber else 1)
            if self.streamer == 'forsenlol' and 'trump_sub' in user.tags:
                num_points *= 0.5
            user.touch(num_points)

    def _dispatcher(self, connection, event):
        if connection == self.connection_manager.get_main_conn() or connection in self.whisper_manager or (self.control_hub is not None and connection == self.control_hub.get_main_conn()):
            do_nothing = lambda c, e: None
            method = getattr(self, "on_" + event.type, do_nothing)
            method(connection, event)

    def start(self):
        """Start the IRC client."""
        self.reactor.process_forever()

    def get_kvi_value(self, key, extra={}):
        if key in self.kvi.data:
            # We check if the value exists first.
            # We don't want to create a bunch of unneccesary KVIData's
            return self.kvi[key].get()
        return 0

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

    def privmsg(self, message, channel=None):
        try:
            if channel is None:
                channel = self.channel

            if self.control_hub is not None and self.control_hub.channel == channel:
                self.control_hub.privmsg(channel, message)
            else:
                self.connection_manager.privmsg(channel, message)
        except Exception:
            log.exception('Exception caught while sending privmsg')

    def c_time_norway(self):
        log.warning('DEPRECATED: use $(time:Europe/Oslo) instead')
        return datetime.now(timezone('Europe/Oslo')).strftime(TyggBot.date_fmt)

    def c_uptime(self):
        return time_since(datetime.now().timestamp(), self.start_time.timestamp())

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

    def c_time_since_latest_deck(self):
        return time_since(time.time(), self.kvi['latest_deck_time'].get())

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

        # If a user types when timed out, we assume he's been unbanned for a good reason and remove his flag.
        if source.timed_out is True:
            source.timed_out = False

        for tag in tags:
            if tag['key'] == 'subscriber':
                if source.subscriber and tag['value'] == '0':
                    source.subscriber = False
                elif not source.subscriber and tag['value'] == '1':
                    source.subscriber = True
            elif tag['key'] == 'emotes' and tag['value']:
                emote_data = tag['value'].split('/')
                for emote in emote_data:
                    try:
                        emote_id, emote_occurrence = emote.split(':')
                        emote_indices = emote_occurrence.split(',')
                        emote_count = len(emote_indices)
                        emote = self.emotes[int(emote_id)]
                        emote.add(emote_count, self.reactor)
                        first_index, last_index = emote_indices[0].split('-')
                        emote_code = msg_raw[int(first_index):int(last_index) + 1]

                        tag_as = None
                        if emote_code.startswith('trump'):
                            tag_as = 'trump_sub'
                        elif emote_code.startswith('eloise'):
                            tag_as = 'eloise_sub'
                        elif emote_code.startswith('forsen'):
                            tag_as = 'forsen_sub'
                        elif emote_code.startswith('nostam'):
                            tag_as = 'nostam_sub'
                        elif emote_code.startswith('reynad'):
                            tag_as = 'reynad_sub'

                        if tag_as is not None:
                            if source.tag_as(tag_as) is True:
                                self.execute_delayed(60 * 60 * 24, source.remove_tag, (tag_as, ))

                        if emote.id is None and emote.code is None:
                            # The emote we just detected is new, set its code.
                            emote.code = emote_code
                            if emote.code not in self.emotes:
                                self.emotes[emote.code] = emote
                    except:
                        log.exception('Exception caught while splitting emote data')
            elif tag['key'] == 'display-name' and tag['value']:
                try:
                    source.update_username(tag['value'])
                except:
                    log.exception('Exception caught while updating a users username')
            elif tag['key'] == 'user-type':
                source.moderator = tag['value'] == 'mod' or source.username == self.streamer

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

                if self.settings['check_links'] and source.level < 500:
                    # Action which will be taken when a bad link is found
                    action = Action(self.timeout, args=[source.username, 20])
                    # First we perform a basic check
                    if self.link_checker.simple_check(url, action) == LinkChecker.RET_FURTHER_ANALYSIS:
                        # If the basic check returns no relevant data, we queue up a proper check on the URL
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

    def quit(self):
        self.commit_all()
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
