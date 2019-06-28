import logging
import socket
import ssl

import irc
from irc.client import InvalidCharacters
from irc.client import MessageTooLong
from irc.client import ServerNotConnectedError
from irc.connection import Factory
from ratelimiter import RateLimiter

from pajbot.tmi import TMI

log = logging.getLogger("pajbot")


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
        if "\n" in string or "\r" in string:
            raise InvalidCharacters("CR/LF not allowed in IRC commands")
        bytes = string.encode("utf-8") + b"\r\n"
        # According to the RFC http://tools.ietf.org/html/rfc2812#page-6,
        # clients should not transmit more than 512 bytes.
        # However, Twitch have raised that limit to 2048 in their servers.
        if len(bytes) > 2048:
            raise MessageTooLong("Messages limited to 2048 bytes including CR/LF")
        if self.socket is None:
            raise ServerNotConnectedError("Not connected.")
        sender = getattr(self.socket, "write", self.socket.send)
        try:
            sender(bytes)
        except socket.error:
            # Ouch!
            self.disconnect("Connection reset by peer.")


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
    def __init__(self, reactor, bot, streamer, control_hub_channel, host, port):
        self.host = host
        self.port = port

        self.streamer = streamer
        self.channel = "#" + self.streamer
        if control_hub_channel:
            self.control_hub_channel = "#" + control_hub_channel
        else:
            self.control_hub_channel = None

        self.reactor = reactor
        self.bot = bot
        self.main_conn = None

    @RateLimiter(max_calls=1, period=2)
    def start(self):
        try:
            self.make_new_connection()

            phrase_data = {"nickname": self.bot.nickname, "version": self.bot.version}

            for p in self.bot.phrases["welcome"]:
                self.bot.privmsg(p.format(**phrase_data))

            # XXX
            self.bot.execute_every(30, lambda: self.main_conn.ping("tmi.twitch.tv"))

            return True
        except:
            log.exception("babyrage")
            return False

    def make_new_connection(self):
        ip = self.host
        port = self.port

        try:
            ssl_factory = Factory(wrapper=ssl.wrap_socket)
            self.main_conn = Connection(self.reactor)
            with self.reactor.mutex:
                self.reactor.connections.append(self.main_conn)
            self.main_conn.connect(
                ip, port, self.bot.nickname, self.bot.password, self.bot.nickname, connect_factory=ssl_factory
            )
            self.main_conn.cap("REQ", "twitch.tv/commands", "twitch.tv/tags")
        except irc.client.ServerConnectionError:
            return False

    def on_disconnect(self, _chatconn):
        log.error("Disconnected from IRC")
        self.start()

    def privmsg(self, channel, message, increase_message=True):
        conn = self.main_conn

        if conn is None or not conn.can_send():
            log.error("No available connections to send messages from. Delaying message a few seconds.")
            self.bot.execute_delayed(2, self.privmsg, (channel, message, increase_message))
            return

        conn.privmsg(channel, message)
        if increase_message:
            conn.num_msgs_sent += 1
            self.bot.execute_delayed(31, conn.reduce_msgs_sent)
