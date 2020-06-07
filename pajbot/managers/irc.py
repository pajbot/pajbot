import logging
import ssl

import socket
from irc.client import InvalidCharacters, MessageTooLong, ServerConnection, ServerNotConnectedError
from irc.connection import Factory
from ratelimiter import RateLimiter

from pajbot.managers.schedule import ScheduleManager

log = logging.getLogger(__name__)


class Connection(ServerConnection):
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


class IRCManager:
    def __init__(self, bot):
        self.bot = bot

        self.conn = None
        self.ping_task = None

        self.num_privmsg_sent = 0
        self.num_whispers_sent_minute = 0
        self.num_whispers_sent_second = 0

        streamer_channel = "#" + self.bot.streamer
        self.channels = [streamer_channel]

        control_hub_channel = self.bot.config["main"].get("control_hub", None)
        if control_hub_channel is not None:
            self.channels.append("#" + control_hub_channel)

        bot.reactor.add_global_handler("all_events", self._dispatcher, -10)
        bot.reactor.add_global_handler("disconnect", self._on_disconnect)
        bot.reactor.add_global_handler("welcome", self._on_welcome)

    @RateLimiter(max_calls=1, period=2)
    def start(self):
        if self.conn is not None or self.ping_task is not None:
            raise AssertionError("start() should not be called while a connection is active")

        try:
            self._make_new_connection()
        except:
            log.exception("Failed to open connection, retrying in 2 seconds")
            self.bot.execute_delayed(2, lambda: self.start())

    def _make_new_connection(self):
        self.conn = Connection(self.bot.reactor)
        with self.bot.reactor.mutex:
            self.bot.reactor.connections.append(self.conn)
        self.conn.connect(
            "irc.chat.twitch.tv",
            6697,
            self.bot.nickname,
            self.bot.password,
            self.bot.nickname,
            connect_factory=Factory(wrapper=ssl.wrap_socket),
        )
        self.conn.cap("REQ", "twitch.tv/commands", "twitch.tv/tags")

        self.ping_task = ScheduleManager.execute_every(30, lambda: self.bot.execute_now(self._send_ping))

    def _send_ping(self):
        if self.conn is not None:
            self.conn.ping("tmi.twitch.tv")

    def privmsg(self, channel, message, is_whisper):
        if self.conn is None or not self._can_send(is_whisper):
            log.error("Not connected or rate limit was reached. Delaying message a few seconds.")
            self.bot.execute_delayed(2, self.privmsg, channel, message, is_whisper)
            return

        self.conn.privmsg(channel, message)

        self.num_privmsg_sent += 1
        self.bot.execute_delayed(31, self._reduce_num_privmsg_sent)

        if is_whisper:
            self.num_whispers_sent_minute += 1
            self.num_whispers_sent_second += 1
            self.bot.execute_delayed(1, self._reduce_num_whispers_sent_second)
            self.bot.execute_delayed(61, self._reduce_num_whispers_sent_minute)

    def whisper(self, username, message):
        self.privmsg(f"#{self.bot.nickname}", f"/w {username} {message}", is_whisper=True)

    def _can_send(self, is_whisper):
        if is_whisper:
            return (
                self.num_privmsg_sent < self.bot.tmi_rate_limits.privmsg_per_30
                and self.num_whispers_sent_second < self.bot.tmi_rate_limits.whispers_per_second
                and self.num_whispers_sent_minute < self.bot.tmi_rate_limits.whispers_per_minute
            )
        else:
            return self.num_privmsg_sent < self.bot.tmi_rate_limits.privmsg_per_30

    def _reduce_num_privmsg_sent(self):
        self.num_privmsg_sent -= 1

    def _reduce_num_whispers_sent_minute(self):
        self.num_whispers_sent_minute -= 1

    def _reduce_num_whispers_sent_second(self):
        self.num_whispers_sent_second -= 1

    def _dispatcher(self, conn, event):
        method = getattr(self.bot, "on_" + event.type, None)
        if method is not None:
            try:
                method(conn, event)
            except:
                log.exception("Logging an uncaught exception (IRC event handler)")

    def _on_disconnect(self, _conn, event):
        log.error(f"Disconnected from IRC ({event.arguments[0]})")
        self.conn = None
        self.ping_task.remove()  # Stops the scheduled task from further executing
        self.ping_task = None
        self.start()

    def _on_welcome(self, conn, _event):
        log.info("Successfully connected and authenticated with IRC")
        conn.join(",".join(self.channels))
