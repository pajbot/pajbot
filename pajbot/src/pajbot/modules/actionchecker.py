from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

import logging

from pajbot.managers.handler import HandlerManager
from pajbot.models.user import User
from pajbot.modules import BaseModule, ModuleSetting

if TYPE_CHECKING:
    from pajbot.bot import Bot

log = logging.getLogger(__name__)


class ActionCheckerModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Action Command Moderation"
    DESCRIPTION = "Dis/allows messages who use the /me command."
    CATEGORY = "Moderation"
    SETTINGS = [
        ModuleSetting(
            key="only_allow_action_messages",
            label="Only allow /me messages",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="allow_timeout_reason",
            label="Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="Lack of /me usage",
            constraints={},
        ),
        ModuleSetting(
            key="disallow_action_messages",
            label="Disallow /me messages",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="disallow_timeout_reason",
            label="Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="No /me usage allowed!",
            constraints={},
        ),
        ModuleSetting(
            key="enabled_by_stream_status",
            label="Enable moderation of the /me command when the stream is:",
            type="options",
            required=True,
            default="Offline and Online",
            options=["Online Only", "Offline Only", "Offline and Online"],
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
            key="timeout_length",
            label="Timeout length",
            type="number",
            required=True,
            placeholder="Timeout length in seconds",
            default=30,
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
            key="disable_warnings",
            label="Disable warning timeouts",
            type="boolean",
            required=True,
            default=False,
        ),
    ]

    def on_message(self, source: User, event: Any, msg_id: str, **rest) -> bool:
        if self.bot is None:
            log.warning("Module bot is None")
            return True

        if self.settings["enabled_by_stream_status"] == "Online Only" and not self.bot.is_online:
            return True

        if self.settings["enabled_by_stream_status"] == "Offline Only" and self.bot.is_online:
            return True

        if source.level >= self.settings["bypass_level"] or source.moderator is True:
            return True

        if event.type == "action" and self.settings["disallow_action_messages"] is True:
            self.bot.delete_or_timeout(
                source,
                self.settings["moderation_action"],
                msg_id,
                self.settings["timeout_length"],
                self.settings["disallow_timeout_reason"],
                disable_warnings=self.settings["disable_warnings"],
            )
            return False

        if event.type != "action" and self.settings["only_allow_action_messages"] is True:
            self.bot.delete_or_timeout(
                source,
                self.settings["moderation_action"],
                msg_id,
                self.settings["timeout_length"],
                self.settings["allow_timeout_reason"],
                disable_warnings=self.settings["disable_warnings"],
            )
            return False

        return True

    def enable(self, bot: Optional[Bot]) -> None:
        HandlerManager.add_handler("on_message", self.on_message, priority=150, run_if_propagation_stopped=True)

    def disable(self, bot: Optional[Bot]) -> None:
        HandlerManager.remove_handler("on_message", self.on_message)
