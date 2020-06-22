import logging

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.modules.chat_alerts import ChatAlertModule
from pajbot.models.stream import StreamManager

log = logging.getLogger(__name__)

class LiveAlertModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Live Alert"
    DESCRIPTION = "Prints a message in chat when the streamer goes live"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = False
    PARENT_MODULE = ChatAlertModule
    SETTINGS = [
        ModuleSetting(
            key="live_message",
            label="Message to post when streamer goes live | Available arguments: {streamer}, {game}, {title}",
            type="text",
            required=True,
            placeholder="{streamer} is now live! PogChamp Streaming {game}: {title}",
            default="{streamer} is now live! PogChamp Streaming {game}: {title}",
            constraints={"max_str_len": 400},
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)

    def on_stream_start (self, bot, stream, **rest):
        live_chat_message = self.settings["live_message"]
        bot.say(live_chat_message.format(streamer=bot.self.streamer, game=stream.self.game, title=stream.self.title))

    def enable(self, bot):
        HandlerManager.add_handler("on_stream_start", self.on_stream_start)

    def disable(self, bot):
        HandlerManager.remove_handler("on_stream_start", self.on_stream_start)
