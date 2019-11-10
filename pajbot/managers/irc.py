import logging

from pajbot.managers.connection import ConnectionManager

log = logging.getLogger(__name__)


def do_nothing(_c, _e):
    pass


class IRCManager:
    def __init__(self, bot):
        self.bot = bot

        self.channels = []

        self.channels.append("#" + self.bot.streamer.login)
        if bot.control_hub is not None:
            self.channels.append("#" + bot.control_hub.login)

        self.connection_manager = ConnectionManager(self.bot.reactor, self.bot, host="irc.chat.twitch.tv", port=6697)

    def start(self):
        self.connection_manager.start()

    def whisper(self, username, message):
        self.connection_manager.privmsg(f"#{self.bot.bot_user.login}", f"/w {username} {message}")

    def privmsg(self, message, channel, increase_message=True):
        self.connection_manager.privmsg(channel, message, increase_message=increase_message)

    def on_disconnect(self, chatconn, event):
        self.connection_manager.on_disconnect(chatconn)

    def _dispatcher(self, connection, event):
        method = getattr(self.bot, "on_" + event.type, do_nothing)
        try:
            method(connection, event)
        except:
            log.exception("Logging an uncaught exception (IRC event handler)")

    def on_welcome(self, conn, event):
        log.info("Successfully connected and authenticated with IRC")
        conn.join(",".join(self.channels))

    def on_connect(self, sock):
        pass
