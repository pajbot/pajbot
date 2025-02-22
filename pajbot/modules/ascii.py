from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import logging

from pajbot.managers.handler import HandlerManager, HandlerResponse, ResponseMeta
from pajbot.message_event import MessageEvent
from pajbot.models.emote import EmoteInstance, EmoteInstanceCountMap
from pajbot.models.user import User
from pajbot.modules.base import BaseModule, ModuleSetting

if TYPE_CHECKING:
    from pajbot.bot import Bot

log = logging.getLogger(__name__)


class AsciiProtectionModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "ASCII Protection"
    DESCRIPTION = "Times out users who post messages that contain too many ASCII characters."
    CATEGORY = "Moderation"
    SETTINGS = [
        ModuleSetting(
            key="enabled_by_stream_status",
            label="Enable moderation of ASCII characters when the stream is:",
            type="options",
            required=True,
            default="Offline and Online",
            options=["Online Only", "Offline Only", "Offline and Online"],
        ),
        ModuleSetting(
            key="min_msg_length",
            label="Minimum message length to be considered bad",
            type="number",
            required=True,
            placeholder="",
            default=70,
            constraints={"min_value": 20, "max_value": 500},
        ),
        ModuleSetting(
            key="moderation_action",
            label="Moderation action to apply",
            type="options",
            required=True,
            default="Timeout",
            options=["Delete", "Timeout"],
        ),
        ModuleSetting(
            key="timeout_online",
            label="Online timeout duration (if moderation action is timeout)",
            type="number",
            required=True,
            placeholder="Timeout length in seconds",
            default=120,
            constraints={"min_value": 1, "max_value": 1209600},
        ),
        ModuleSetting(
            key="timeout_offline",
            label="Offline Timeout duration (if moderation action is timeout)",
            type="number",
            required=True,
            placeholder="Timeout length in seconds",
            default=120,
            constraints={"min_value": 1, "max_value": 1209600},
        ),
        ModuleSetting(
            key="bypass_level",
            label="Level to bypass module",
            type="number",
            required=True,
            placeholder="",
            default=500,
            constraints={"min_value": 100, "max_value": 1000},
        ),
        ModuleSetting(
            key="timeout_reason",
            label="Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="Too many ASCII characters",
            constraints={},
        ),
        ModuleSetting(
            key="disable_warnings",
            label="Disable warning timeouts",
            type="boolean",
            required=True,
            default=False,
        ),
    ]

    @staticmethod
    def check_message(message):
        if len(message) <= 0:
            return False

        non_alnum = sum(not c.isalnum() for c in message)
        ratio = non_alnum / len(message)
        if (len(message) > 240 and ratio > 0.8) or ratio > 0.93:
            return True
        return False

    async def on_message(
        self,
        source: User,
        message: str,
        emote_instances: list[EmoteInstance],
        emote_counts: EmoteInstanceCountMap,
        is_whisper: bool,
        urls: list[str],
        msg_id: str | None,
        event: MessageEvent,
        meta: ResponseMeta,
    ) -> HandlerResponse:
        if is_whisper:
            return HandlerResponse.null()

        if self.bot is None:
            return HandlerResponse.null()

        if msg_id is None:
            return HandlerResponse.null()

        if self.settings["enabled_by_stream_status"] == "Online Only" and not self.bot.is_online:
            return HandlerResponse.null()

        if self.settings["enabled_by_stream_status"] == "Offline Only" and self.bot.is_online:
            return HandlerResponse.null()

        if source.level >= self.settings["bypass_level"] or source.moderator is True:
            return HandlerResponse.null()

        if len(message) <= self.settings["min_msg_length"]:
            return HandlerResponse.null()

        if AsciiProtectionModule.check_message(message) is False:
            return HandlerResponse.null()

        return HandlerResponse.do_delete_or_timeout(
            source.id,
            self.settings["moderation_action"],
            msg_id,
            self.settings["timeout_online"] if self.bot.is_online else self.settings["timeout_offline"],
            reason=self.settings["timeout_reason"],
            disable_warnings=self.settings["disable_warnings"],
        )

    def enable(self, bot: Optional[Bot]) -> None:
        if bot:
            HandlerManager.register_on_message(self.on_message, priority=150)

    def disable(self, bot: Optional[Bot]) -> None:
        if bot:
            HandlerManager.unregister_on_message(self.on_message)
