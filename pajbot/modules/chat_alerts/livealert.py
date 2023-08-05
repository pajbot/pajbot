from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import logging

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule, ModuleSetting
from pajbot.modules.chat_alerts import ChatAlertModule

if TYPE_CHECKING:
    from pajbot.bot import Bot

log = logging.getLogger(__name__)


class LiveAlertModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Live Alert"
    DESCRIPTION = "Prints a message in chat when the streamer goes live"
    CATEGORY = "Feature"
    PARENT_MODULE = ChatAlertModule
    SETTINGS = [
        ModuleSetting(
            key="message_type",
            label="Method to use when sending live messages",
            type="options",
            required=True,
            default="announce",
            options=["announce", "say", "me"],
        ),
        ModuleSetting(
            key="live_message",
            label="Message to post when streamer goes live | Available arguments: {streamer}, {game}, {title}",
            type="text",
            required=True,
            placeholder="{streamer} is now live! PogChamp Streaming {game}: {title}",
            default="{streamer} is now live! PogChamp Streaming {game}: {title}",
            constraints={"max_str_len": 400},
        ),
        ModuleSetting(
            key="extra_message",
            label="Extra message to post after the initial live message is posted. Leave empty to disable | Available arguments: {streamer}",
            type="text",
            required=False,
            placeholder="@{streamer} TWEET THAT YOU'RE LIVE OMGScoots",
            default="",
            constraints={"max_str_len": 400},
        ),
    ]

    def __init__(self, bot: Optional[Bot]) -> None:
        super().__init__(bot)

    def on_stream_start(self) -> bool:
        assert self.bot is not None

        arguments = {
            "streamer": self.bot.streamer_display,
            "game": self.bot.stream_manager.game,
            "title": self.bot.stream_manager.title,
        }

        self.bot.send_message(self.get_phrase("live_message", **arguments), method=self.settings["message_type"])

        if self.settings["extra_message"] != "":
            self.bot.send_message(self.get_phrase("extra_message", **arguments), method=self.settings["message_type"])

        return True

    def enable(self, bot: Optional[Bot]) -> None:
        if bot is not None:
            HandlerManager.add_handler("on_stream_start", self.on_stream_start)

    def disable(self, bot: Optional[Bot]) -> None:
        if bot is not None:
            HandlerManager.remove_handler("on_stream_start", self.on_stream_start)
