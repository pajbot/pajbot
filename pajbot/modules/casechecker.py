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


class CaseCheckerModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Case Checker"
    DESCRIPTION = "Times out users who post messages that contain lowercase/uppercase letters."
    CATEGORY = "Moderation"
    SETTINGS = [
        ModuleSetting(
            key="online_chat_only", label="Only enabled in online chat", type="boolean", required=True, default=True
        ),
        ModuleSetting(
            key="offline_chat_only", label="Only enabled in offline chat", type="boolean", required=True, default=False
        ),
        ModuleSetting(
            key="subscriber_exemption",
            label="Exempt subscribers from case-based timeouts",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="vip_exemption",
            label="Exempt VIPs from case-based timeouts",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="moderation_action",
            label="Moderation action to apply",
            type="options",
            required=True,
            default="Timeout",
            options=["Timeout", "Delete"],
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
            key="lowercase_timeouts", label="Enable lowercase timeouts", type="boolean", required=True, default=False
        ),
        ModuleSetting(
            key="lowercase_timeout_duration",
            label="Lowercase Timeout duration",
            type="number",
            required=True,
            placeholder="",
            default=3,
            constraints={"min_value": 1, "max_value": 1209600},
        ),
        ModuleSetting(
            key="lowercase_timeout_reason",
            label="Lowercase Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="Too many lowercase characters",
            constraints={"max_str_len": 500},
        ),
        ModuleSetting(
            key="max_lowercase",
            label="Maximum amount of lowercase characters allowed in a message.  This setting is checked prior to the percentage-based lowercase check.",
            type="number",
            required=True,
            placeholder="",
            default=50,
            constraints={"min_value": 0, "max_value": 500},
        ),
        ModuleSetting(
            key="min_lowercase_characters",
            label="Minimum amount of lowercase characters before checking for a percentage",
            type="number",
            required=True,
            placeholder="",
            default=8,
            constraints={"min_value": 0, "max_value": 500},
        ),
        ModuleSetting(
            key="lowercase_percentage",
            label="Maximum percent of lowercase letters allowed in message",
            type="number",
            required=True,
            placeholder="",
            default=60,
            constraints={"min_value": 0, "max_value": 100},
        ),
        ModuleSetting(
            key="uppercase_timeouts", label="Enable uppercase timeouts", type="boolean", required=True, default=False
        ),
        ModuleSetting(
            key="uppercase_timeout_duration",
            label="Uppercase Timeout duration",
            type="number",
            required=True,
            placeholder="",
            default=3,
            constraints={"min_value": 1, "max_value": 1209600},
        ),
        ModuleSetting(
            key="uppercase_timeout_reason",
            label="Uppercase Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="Too many uppercase characters",
            constraints={"max_str_len": 500},
        ),
        ModuleSetting(
            key="max_uppercase",
            label="Maximum amount of uppercase characters allowed in a message. This setting is checked prior to the percentage-based uppercase check.",
            type="number",
            required=True,
            placeholder="",
            default=50,
            constraints={"min_value": 0, "max_value": 500},
        ),
        ModuleSetting(
            key="min_uppercase_characters",
            label="Minimum amount of uppercase characters before checking for a percentage",
            type="number",
            required=True,
            placeholder="",
            default=8,
            constraints={"min_value": 0, "max_value": 500},
        ),
        ModuleSetting(
            key="uppercase_percentage",
            label="Maximum percent of uppercase letters allowed in message",
            type="number",
            required=True,
            placeholder="",
            default=60,
            constraints={"min_value": 0, "max_value": 100},
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

        if msg_id is None:
            # Module can only handle messages from Twitch chat
            return HandlerResponse.null()

        if source.level >= self.settings["bypass_level"] or source.moderator is True:
            return HandlerResponse.null()

        if (self.settings["online_chat_only"] and not self.bot.is_online) or (
            self.settings["offline_chat_only"] and self.bot.is_online
        ):
            return HandlerResponse.null()

        if self.settings["subscriber_exemption"] and source.subscriber is True:
            return HandlerResponse.null()

        if self.settings["vip_exemption"] and source.vip is True:
            return HandlerResponse.null()

        amount_lowercase = sum(1 for c in message if c.islower())
        if self.settings["lowercase_timeouts"] is True:
            if amount_lowercase >= self.settings["max_lowercase"]:
                res = HandlerResponse()
                res.delete_or_timeout(
                    source.id,
                    self.settings["moderation_action"],
                    msg_id,
                    self.settings["lowercase_timeout_duration"],
                    reason=self.settings["lowercase_timeout_reason"],
                    disable_warnings=self.settings["disable_warnings"],
                )
                return res

            if (
                amount_lowercase >= self.settings["min_lowercase_characters"]
                and (amount_lowercase / len(message)) * 100 >= self.settings["lowercase_percentage"]
            ):
                res = HandlerResponse()
                res.delete_or_timeout(
                    source.id,
                    self.settings["moderation_action"],
                    msg_id,
                    self.settings["lowercase_timeout_duration"],
                    reason=self.settings["lowercase_timeout_reason"],
                    disable_warnings=self.settings["disable_warnings"],
                )
                return res

        amount_uppercase = sum(1 for c in message if c.isupper())
        if self.settings["uppercase_timeouts"] is True:
            if amount_uppercase >= self.settings["max_uppercase"]:
                res = HandlerResponse()
                res.delete_or_timeout(
                    source.id,
                    self.settings["moderation_action"],
                    msg_id,
                    self.settings["uppercase_timeout_duration"],
                    reason=self.settings["uppercase_timeout_reason"],
                    disable_warnings=self.settings["disable_warnings"],
                )
                return res

            if (
                amount_uppercase >= self.settings["min_uppercase_characters"]
                and (amount_uppercase / len(message)) * 100 >= self.settings["uppercase_percentage"]
            ):
                res = HandlerResponse()
                res.delete_or_timeout(
                    source.id,
                    self.settings["moderation_action"],
                    msg_id,
                    self.settings["uppercase_timeout_duration"],
                    reason=self.settings["uppercase_timeout_reason"],
                    disable_warnings=self.settings["disable_warnings"],
                )
                return res

        return HandlerResponse.null()

    def enable(self, bot: Optional[Bot]) -> None:
        if bot:
            HandlerManager.register_on_message(self.on_message, priority=150)

    def disable(self, bot: Optional[Bot]) -> None:
        if bot:
            HandlerManager.unregister_on_message(self.on_message)
