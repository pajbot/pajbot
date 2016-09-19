import logging
import random
import socket
import urllib

import irc
from irc.client import InvalidCharacters
from irc.client import MessageTooLong
from irc.client import ServerNotConnectedError

from pajbot.utils import find

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


class Connection:
    def __init__(self, conn):
        self.conn = conn
        self.num_msgs_sent = 0
        self.in_channel = False

        return

    def reduce_msgs_sent(self):
        self.num_msgs_sent -= 1


class ConnectionManager:
    def __init__(self, reactor, bot, message_limit, streamer, backup_conns=2):
        self.backup_conns_number = backup_conns
        self.streamer = streamer
        self.channel = '#' + self.streamer

        self.reactor = reactor
        self.bot = bot
        self.message_limit = message_limit

        self.connlist = []

        self.maintenance_lock = False

    def start(self):
        log.debug('Starting connection manager')
        try:
            for i in range(0, self.backup_conns_number + 1):
                newconn = self.make_new_connection()
                self.connlist.append(newconn)

            self.get_main_conn()

            welcome = '{nickname} {version} running!'
            phrase_data = {
                'nickname': self.bot.nickname,
                'version': self.bot.version,
                 }

            self.bot.say(welcome.format(**phrase_data))

            self.reactor.execute_every(4, self.run_maintenance)
            return True
        except:
            return False

    def run_maintenance(self):
        if self.maintenance_lock:
            return

        self.maintenance_lock = True
        clean_conns_count = 0
        tmp = []  # new list of connections
        for connection in self.connlist:
            if not connection.conn.is_connected():
                log.debug('Removing connection because not connected')
                continue  # don't want this connection in the new list

            if connection.num_msgs_sent <= 5:
                if clean_conns_count >= self.backup_conns_number and connection.num_msgs_sent == 0:  # we have more connections than needed
                    log.debug('Removing connection because we have enough backup')
                    connection.conn.close()
                    continue  # don't want this connection
                else:
                    clean_conns_count += 1

            tmp.append(connection)

        self.connlist = tmp  # replace the old list with the newly constructed one
        need_more = self.backup_conns_number - clean_conns_count

        for i in range(0, need_more):  # add as many fresh connections as needed
            newconn = self.make_new_connection()
            self.connlist.append(newconn)

        self.get_main_conn()
        self.maintenance_lock = False

    def get_main_conn(self):
        for connection in self.connlist:
            if connection.conn.is_connected():
                if not connection.in_channel:
                    if irc.client.is_channel(self.channel):
                        connection.conn.join(self.channel)
                        log.debug('Joined channel')
                        connection.in_channel = True

                return connection.conn

        self.run_maintenance()
        return self.get_main_conn()

    def get_chat_server(self, streamer):
        data = None
        try:
            data = self.bot.twitchapi.get(['channels', streamer, 'chat_properties'])
        except urllib.error.HTTPError:
            log.error('An unhandled HTTP Error occured when trying to create a new connection.')

        if data is None:
            # return this default shit in case the data is bad
            # TODO: We should be able to specify in the config if the fallback IP should be
            #       an IP on the event server or not.
            return 'irc.twitch.tv', 6667

        server = random.choice(data['chat_servers'])
        ip, port = server.split(':')
        return ip, int(port)

    def make_new_connection(self):
        log.debug('Creating a new IRC connection...')
        log.debug('Fetching random IRC server... ({0})'.format(self.streamer))

        ip, port = self.get_chat_server(self.streamer)

        log.debug('Fetched {0}:{1}'.format(ip, port))

        try:
            newconn = CustomServerConnection(self.reactor)
            with self.reactor.mutex:
                self.reactor.connections.append(newconn)
            newconn.connect(ip, port, self.bot.nickname, self.bot.password, self.bot.nickname)
            log.debug('Connecting to IRC server...')
            newconn.cap('REQ', 'twitch.tv/membership')
            newconn.cap('REQ', 'twitch.tv/commands')
            newconn.cap('REQ', 'twitch.tv/tags')

            connection = Connection(newconn)
            return connection
        except irc.client.ServerConnectionError:
            return

        else:
            log.error('No proper data returned when fetching IRC servers')
            return None

    def on_disconnect(self, chatconn):
        self.run_maintenance()
        return

    def privmsg(self, channel, message, increase_message=True):
        if increase_message:
            conn = find(lambda c: c.conn.is_connected() and c.num_msgs_sent < self.message_limit, self.connlist)
        else:
            conn = find(lambda c: c.conn.is_connected(), self.connlist)

        if conn is None:
            log.error('No available connections to send messages from. Delaying message a few seconds.')
            self.reactor.execute_delayed(2, self.privmsg, (channel, message, increase_message))
            return False

        conn.conn.privmsg(channel, message)
        if increase_message:
            conn.num_msgs_sent += 1
            self.reactor.execute_delayed(31, conn.reduce_msgs_sent)

            if conn.num_msgs_sent >= self.message_limit:
                self.run_maintenance()
