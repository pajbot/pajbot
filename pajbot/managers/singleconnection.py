import abc
import logging

import irc
import six

from pajbot.managers.connection import CustomServerConnection

log = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class ReconnectStrategy(object):
    """
    An abstract base class describing the interface used by
    SingleServerIRCBot for handling reconnect following
    disconnect events.
    """
    @abc.abstractmethod
    def run(self, bot):
        """
        Invoked by the bot on disconnect. Here
        a strategy can determine how to react to a
        disconnect.
        """


class StaticInterval(ReconnectStrategy):
    def __init__(self, interval):
        self.interval = interval
        self._check_scheduled = False

    def run(self, bot):
        self.bot = bot

        if self._check_scheduled:
            return

        log.info('Attempting to reconnect...')

        self.bot.execute_delayed(self.interval, self.check)
        self._check_scheduled = True

    def check(self):
        self._check_scheduled = False
        if not self.bot.relay_connection.is_connected():
            self.run(self.bot)
            self.bot._connect()


class SingleConnectionManager:
    def __init__(self, reactor, host, relay_password, username, password):
        self.reactor = reactor
        self.host = host
        self.username = username
        self.password = '{};{}'.format(relay_password, password)

        # Try to reconnect every 3 seconds
        self.recon = StaticInterval(3)

        self.relay_connection = None

    def start(self):
        self.relay_connection = CustomServerConnection(self.reactor)
        with self.reactor.mutex:
            self.reactor.connections.append(self.relay_connection)

        self._connect()

    def _connect(self):
        ip, port = self.host.split(':')
        port = int(port)
        log.debug('Connecting to relay {}:{}'.format(ip, port))
        try:
            self.relay_connection.connect(ip, port, self.username, self.password, self.username)
        except irc.client.ServerConnectionError:
            log.error('Error connecting to {}:{}'.format(ip, port))
            self.recon.run(self)

    def privmsg(self, channel, message):
        try:
            return self.relay_connection.privmsg(channel, message)
        except irc.client.ServerNotConnectedError:
            log.warning('Unable to send message "{}", not connected to the relay.'.format(message))
            pass

    def whisper(self, username, message):
        return self.relay_connection.privmsg('#jtv', '/w {0} {1}'.format(username, message))

    def on_disconnect(self):
        self.recon.run(self)
