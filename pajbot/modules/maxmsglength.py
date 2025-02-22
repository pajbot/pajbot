from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

import logging

from pajbot.managers.handler import HandlerManager, HandlerResponse, ResponseMeta
from pajbot.message_event import MessageEvent
from pajbot.models.user import User
from pajbot.modules import BaseModule, ModuleSetting

if TYPE_CHECKING:
    from pajbot.bot import Bot

log = logging.getLogger(__name__)


class MaxMsgLengthModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Maximum Message Length"
    DESCRIPTION = "Times out users who post messages that contain too many characters."
    CATEGORY = "Moderation"
    SETTINGS = [
        ModuleSetting(
            key="moderation_action",
            label="Moderation action to apply",
            type="options",
            required=True,
            default="Timeout",
            options=["Timeout", "Delete"],
        ),
        ModuleSetting(
            key="max_msg_length",
            label="Max message length (Online chat)",
            type="number",
            required=True,
            placeholder="",
            default=400,
            constraints={"min_value": 1, "max_value": 500},
        ),
        ModuleSetting(
            key="max_msg_length_offline",
            label="Max message length (Offline chat)",
            type="number",
            required=True,
            placeholder="",
            default=400,
            constraints={"min_value": 1, "max_value": 500},
        ),
        ModuleSetting(
            key="timeout_length",
            label="Timeout length",
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
            default="Message too long",
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

    async def on_message(
        self,
        source: User,
        message: str,
        emote_instances: Any,
        emote_counts: Any,
        is_whisper: bool,
        urls: Any,
        msg_id: str | None,
        event: MessageEvent,
        meta: ResponseMeta,
    ) -> HandlerResponse:
        if self.bot is None:
            # Bot must be set
            return HandlerResponse.null()

        if is_whisper:
            return HandlerResponse.null()

        if msg_id is None:
            # Module can only handle messages from Twitch chat
            return HandlerResponse.null()

        if source.level >= self.settings["bypass_level"] or source.moderator is True:
            return HandlerResponse.null()

        if self.bot.is_online:
            if len(message) > self.settings["max_msg_length"]:
                return HandlerResponse.do_delete_or_timeout(
                    source.id,
                    self.settings["moderation_action"],
                    msg_id,
                    self.settings["timeout_length"],
                    reason=self.settings["timeout_reason"],
                    disable_warnings=self.settings["disable_warnings"],
                )
        else:
            if len(message) > self.settings["max_msg_length_offline"]:
                return HandlerResponse.do_delete_or_timeout(
                    source.id,
                    self.settings["moderation_action"],
                    msg_id,
                    self.settings["timeout_length"],
                    reason=self.settings["timeout_reason"],
                    disable_warnings=self.settings["disable_warnings"],
                )

        return HandlerResponse.null()

    def enable(self, bot: Optional[Bot]) -> None:
        if bot:
            HandlerManager.register_on_message(self.on_message, priority=150)

    def disable(self, bot: Optional[Bot]) -> None:
        if bot:
            HandlerManager.unregister_on_message(self.on_message)
