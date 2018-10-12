import logging

from pajbot.managers.connection import ConnectionManager
from pajbot.managers.singleconnection import SingleConnectionManager
from pajbot.managers.whisperconnection import WhisperConnectionManager

log = logging.getLogger(__name__)


class TMI:
    message_limit = 90
    whispers_message_limit = 20
    whispers_limit_interval = 5  # in seconds


def do_nothing(c, e):
    pass


class IRCManager:
    def __init__(self, bot):
        self.bot = bot

        self.username = self.bot.nickname
        self.password = self.bot.password
        self.channel = '#' + self.bot.streamer
        self.control_hub_channel = self.bot.config['main'].get('control_hub', None)
        if self.control_hub_channel:
            self.control_hub_channel = '#' + self.control_hub_channel

    def start(self):
        log.warn('Missing implementation of IRCManager::start()')

    def whisper(self, username, message):
        log.warn('Missing implementation of IRCManager::whisper()')

    def privmsg(self, message, channel, increase_message=True):
        log.warn('Missing implementation of IRCManager::privmsg()')

    def on_disconnect(self, chatconn, event):
        log.warn('Missing implementation of IRCManager::on_disconnect()')

    def quit(self):
        pass

    def _dispatcher(self, connection, event):
        log.warn('Missing implementation of IRCManager::_dispatcher()')

    def on_welcome(self, chatconn, event):
        pass

    def on_connect(self, sock):
        pass


class SingleIRCManager(IRCManager):
    first_welcome = True

    def __init__(self, bot):
        super().__init__(bot)

        self.relay_host = bot.config['main'].get('relay_host')
        self.relay_password = bot.config['main'].get('relay_password')

        self.connection_manager = SingleConnectionManager(self.bot.reactor, self.relay_host, self.relay_password, self.username, self.password)

    def whisper(self, username, message):
        return self.connection_manager.whisper(username, message)

    def privmsg(self, message, channel, increase_message=True):
        return self.connection_manager.privmsg(channel, message)

    def _dispatcher(self, connection, event):
        method = getattr(self.bot, 'on_' + event.type, do_nothing)
        method(connection, event)

    def start(self):
        return self.connection_manager.start()

    def on_welcome(self, chatconn, event):
        if self.first_welcome:
            self.first_welcome = False
            welcome = '{nickname} {version} running!'
            phrase_data = {
                'nickname': self.bot.nickname,
                'version': self.bot.version,
                 }

            self.bot.say(welcome.format(**phrase_data))

    def on_connect(self, sock):
        self.connection_manager.relay_connection.join(self.channel)
        if self.control_hub_channel:
            self.connection_manager.relay_connection.join(self.control_hub_channel)

    def on_disconnect(self, chatconn, event):
        log.error('Lost connection to relay')
        return self.connection_manager.on_disconnect()


class MultiIRCManager(IRCManager):
    def __init__(self, bot):
        super().__init__(bot)

        self.connection_manager = ConnectionManager(self.bot.reactor, self.bot, TMI.message_limit, streamer=self.bot.streamer)
        chub = self.bot.config['main'].get('control_hub', None)
        if chub is not None:
            self.control_hub = ConnectionManager(self.bot.reactor, self.bot, TMI.message_limit, streamer=chub, backup_conns=1)
        else:
            self.control_hub = None

        # XXX
        self.bot.execute_every(30, lambda: self.connection_manager.get_main_conn().ping('tmi.twitch.tv'))

        self.whisper_manager = WhisperConnectionManager(self.bot.reactor, self.bot, self.bot.streamer, TMI.whispers_message_limit, TMI.whispers_limit_interval)
        self.whisper_manager.start(accounts=[{'username': self.username, 'oauth': self.password, 'can_send_whispers': self.bot.config.getboolean('main', 'add_self_as_whisper_account')}])

    def whisper(self, username, message):
        if self.whisper_manager:
            self.whisper_manager.whisper(username, message)
        else:
            log.debug('No whisper conn set up.')

    def on_disconnect(self, chatconn, event):
        if chatconn in self.whisper_manager:
            log.debug('Whispers: Disconnecting from Whisper server')
            self.whisper_manager.on_disconnect(chatconn)
        else:
            log.debug('Disconnected from IRC server')
            self.connection_manager.on_disconnect(chatconn)

    def _dispatcher(self, connection, event):
        if connection == self.connection_manager.get_main_conn() or connection in self.whisper_manager or (self.control_hub is not None and connection == self.control_hub.get_main_conn()):
            method = getattr(self.bot, 'on_' + event.type, do_nothing)
            method(connection, event)

    def privmsg(self, message, channel, increase_message=True):
        try:
            if self.control_hub is not None and self.control_hub.channel == channel:
                self.control_hub.privmsg(channel, message)
            else:
                self.connection_manager.privmsg(channel, message, increase_message=increase_message)
        except Exception:
            log.exception('Exception caught while sending privmsg')

    def start(self):
        self.connection_manager.start()

    def quit(self):
        if self.whisper_manager:
            self.whisper_manager.quit()
