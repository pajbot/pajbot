from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import logging

from pajbot.managers.handler import HandlerManager
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

    def on_message(self, source: User, message: str, whisper: bool, msg_id: str, **rest) -> bool:
        if self.bot is None:
            log.warning("Module bot is None")
            return True

        if whisper:
            return True
        if source.level >= self.settings["bypass_level"] or source.moderator:
            return True

        if self.bot.is_online:
            if len(message) > self.settings["max_msg_length"]:
                self.bot.delete_or_timeout(
                    source,
                    self.settings["moderation_action"],
                    msg_id,
                    self.settings["timeout_length"],
                    self.settings["timeout_reason"],
                    disable_warnings=self.settings["disable_warnings"],
                )
                return False
        else:
            if len(message) > self.settings["max_msg_length_offline"]:
                self.bot.delete_or_timeout(
                    source,
                    self.settings["moderation_action"],
                    msg_id,
                    self.settings["timeout_length"],
                    self.settings["timeout_reason"],
                    disable_warnings=self.settings["disable_warnings"],
                )
                return False

        return True

    def enable(self, bot: Optional[Bot]) -> None:
        HandlerManager.add_handler("on_message", self.on_message, priority=150, run_if_propagation_stopped=True)

    def disable(self, bot: Optional[Bot]) -> None:
        HandlerManager.remove_handler("on_message", self.on_message)
