import logging

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule, ModuleSetting

log = logging.getLogger(__name__)


class DefaultChatStatesModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Default Chat States"
    DESCRIPTION = "Enforces certain chat states when the streamer goes online/offline"
    CATEGORY = "Moderation"
    ENABLED_DEFAULT = False
    ONLINE_PHRASE = "Goes Online"
    OFFLINE_PHRASE = "Goes Offline"
    NEVER_PHRASE = "Never"
    PHRASE_OPTIONS = [ONLINE_PHRASE, OFFLINE_PHRASE, NEVER_PHRASE]
    SETTINGS = [
        ModuleSetting(
            key="emoteonly",
            label="Enable emote only mode when the stream...",
            type="options",
            required=True,
            default=NEVER_PHRASE,
            options=PHRASE_OPTIONS,
        ),
        ModuleSetting(
            key="subonly",
            label="Enable subscriber only mode when the stream...",
            type="options",
            required=True,
            default=NEVER_PHRASE,
            options=PHRASE_OPTIONS,
        ),
        ModuleSetting(
            key="r9k",
            label="Enable R9K mode when the stream...",
            type="options",
            required=True,
            default=NEVER_PHRASE,
            options=PHRASE_OPTIONS,
        ),
        ModuleSetting(
            key="slow_option",
            label="Enable slow mode when the stream...",
            type="options",
            required=True,
            default=NEVER_PHRASE,
            options=PHRASE_OPTIONS,
        ),
        ModuleSetting(
            key="slow_time",
            label="Amount of seconds to use when setting slow mode",
            type="number",
            required=True,
            placeholder="30",
            default=30,
            constraints={"min_value": 1, "max_value": 1800},
        ),
        ModuleSetting(
            key="followersonly_option",
            label="Enable followers only mode when the stream...",
            type="options",
            required=True,
            default=NEVER_PHRASE,
            options=PHRASE_OPTIONS,
        ),
        ModuleSetting(
            key="followersonly_time",
            label="Amount of time to use when setting followers only mode | Format is number followed by time format. E.g. 30m, 1 week, 5 days 12 hours",
            type="text",
            required=False,
            placeholder="",
            default="",
            constraints={},
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)

    def on_stream_start(self, **rest):
        if self.settings["emoteonly"] == "Going Online":
            self.bot.privmsg(".emoteonly")

        if self.settings["subonly"] == "Going Online":
            self.bot.privmsg(".subonly")

        if self.settings["r9k"] == "Going Online":
            self.bot.privmsg(".uniquechat")

        if self.settings["slow_option"] == "Going Online":
            slow_time = self.settings["slow_time"]
            self.bot.privmsg(f".slow {slow_time}")

        if self.settings["followersonly_option"] == "Going Online":
            if self.settings["followersonly_time"] == "":
                self.bot.privmsg(".followers")
            else:
                follower_time = self.settings["followersonly_time"]
                self.bot.privmsg(f".followers {follower_time}")

    def on_stream_stop(self, **rest):
        if self.settings["emoteonly"] == "Going Offline":
            self.bot.privmsg(".emoteonly")

        if self.settings["subonly"] == "Going Offline":
            self.bot.privmsg(".subonly")

        if self.settings["r9k"] == "Going Offline":
            self.bot.privmsg(".uniquechat")

        if self.settings["slow_option"] == "Going Offline":
            slow_time = self.settings["slow_time"]
            self.bot.privmsg(f".slow {slow_time}")

        if self.settings["followersonly_option"] == "Going Offline":
            if self.settings["followersonly_time"] == "":
                self.bot.privmsg(".followers")
            else:
                follower_time = self.settings["followersonly_time"]
                self.bot.privmsg(f".followers {follower_time}")

    def enable(self, bot):
        HandlerManager.add_handler("on_stream_start", self.on_stream_start)
        HandlerManager.add_handler("on_stream_stop", self.on_stream_stop)

    def disable(self, bot):
        HandlerManager.remove_handler("on_stream_start", self.on_stream_start)
        HandlerManager.remove_handler("on_stream_stop", self.on_stream_stop)
