import logging
import random
import socket
import ssl

import irc
from irc.client import InvalidCharacters
from irc.client import MessageTooLong
from irc.client import ServerNotConnectedError

from pajbot.tmi import TMI

log = logging.getLogger('pajbot')


class CustomServerConnection(irc.client.ServerConnection):
    """
    We override the default irc.clientServerConnection because want to be able
    to send strings that are 2048(?) bytes long. This is not in accordance with the IRC
    standards, but it's the limit the Twitch IRC servers use.
    """
    def send_raw(self, string):
        """Send raw string to the server.

        The string will be padded with appropriate CR LF.
        """
        # The string should not contain any carriage return other than the
        # one added here.
        if '\n' in string:
            raise InvalidCharacters(
                'Carriage returns not allowed in privmsg(text)')
        bytes = string.encode('utf-8') + b'\r\n'
        # According to the RFC http://tools.ietf.org/html/rfc2812#page-6,
        # clients should not transmit more than 512 bytes.
        # However, Twitch have raised that limit to 2048 in their servers.
        if len(bytes) > 2048:
            raise MessageTooLong(
                'Messages limited to 2048 bytes including CR/LF')
        if self.socket is None:
            raise ServerNotConnectedError('Not connected.')
        sender = getattr(self.socket, 'write', self.socket.send)
        try:
            sender(bytes)
        except socket.error:
            # Ouch!
            self.disconnect('Connection reset by peer.')


class Connection(CustomServerConnection):
    def __init__(self, reactor):
        super().__init__(reactor)

        self.num_msgs_sent = 0
        self.in_channel = False

    def reduce_msgs_sent(self):
        self.num_msgs_sent -= 1

    def can_send(self):
        return self.num_msgs_sent < TMI.message_limit


class ConnectionManager:
    def __init__(self, reactor, bot, streamer, control_hub_channel):
        self.streamer = streamer
        self.channel = '#' + self.streamer
        if len(control_hub_channel) > 0:
            self.control_hub_channel = '#' + control_hub_channel
        else:
            self.control_hub_channel = ''

        self.reactor = reactor
        self.bot = bot
        self.main_conn = None

        self.maintenance_lock = False

    def start(self):
        log.debug('Starting connection manager')
        try:
            self.main_conn = self.make_new_connection()

            phrase_data = {
                'nickname': self.bot.nickname,
                'version': self.bot.version,
                 }

            for p in self.bot.phrases['welcome']:
                self.bot.privmsg(p.format(**phrase_data))

            self.run_maintenance()
            self.bot.execute_every(4, self.run_maintenance)
            return True
        except:
            log.exception('babyrage')
            return False

    def run_maintenance(self):
        if self.maintenance_lock:
            log.debug('skipping due to maintenance lock')
            return

        self.maintenance_lock = True
        if self.main_conn is None:
            self.main_conn = self.make_new_connection()
            self.maintenance_lock = False
            return

        if self.main_conn.is_connected():
            if not self.main_conn.in_channel:
                if irc.client.is_channel(self.channel):
                    self.main_conn.join(self.channel)
                    log.debug('Joined channel')

                if irc.client.is_channel(self.control_hub_channel):
                    self.main_conn.join(self.control_hub_channel)
                    log.debug('Joined channel')

                self.main_conn.in_channel = True

        self.maintenance_lock = False

    def get_main_conn(self):
        if self.main_conn is None:
            self.run_maintenance()
            return self.get_main_conn()

        return self.main_conn

    """
    This method returns a random IRC server from a list of valid twitch IRC servers.
    The returned servers accept unencrypted IRC traffic. (they are not SSL servers)
    """
    def get_chat_server(self):
        servers = [
            {'host': 'irc.chat.twitch.tv', 'port': 6697},
            {'host': 'irc.chat.twitch.tv', 'port': 443},
        ]

        server = random.choice(servers)
        return server['host'], server['port']

    def make_new_connection(self):
        log.debug('Creating a new IRC connection...')
        log.debug('Selecting random IRC server... ({0})'.format(self.streamer))

        ip, port = self.get_chat_server()

        log.debug('Selected {0}:{1}'.format(ip, port))

        try:
            ssl_factory = irc.connection.Factory(wrapper=ssl.wrap_socket)
            newconn = Connection(self.reactor)
            with self.reactor.mutex:
                self.reactor.connections.append(newconn)
            newconn.connect(ip, port, self.bot.nickname, self.bot.password, self.bot.nickname, connect_factory=ssl_factory)
            log.debug('Connecting to IRC server...')
            newconn.cap('REQ', 'twitch.tv/membership')
            newconn.cap('REQ', 'twitch.tv/commands')
            newconn.cap('REQ', 'twitch.tv/tags')

            return newconn
        except irc.client.ServerConnectionError:
            return

        else:
            log.error('No proper data returned when fetching IRC servers')
            return None

    def on_disconnect(self, chatconn):
        self.run_maintenance()
        return

    def privmsg(self, channel, message, increase_message=True):
        conn = self.get_main_conn()

        if conn is None or not conn.can_send():
            log.error('No available connections to send messages from. Delaying message a few seconds.')
            self.bot.execute_delayed(2, self.privmsg, (channel, message, increase_message))
            return False

        conn.privmsg(channel, message)
        if increase_message:
            conn.num_msgs_sent += 1
            self.bot.execute_delayed(31, conn.reduce_msgs_sent)
