from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import logging

from pajbot.managers.handler import HandlerManager
from pajbot.models.emote import EmoteInstance
from pajbot.models.user import User
from pajbot.modules import BaseModule, ModuleSetting

if TYPE_CHECKING:
    from pajbot.bot import Bot

log = logging.getLogger(__name__)


class NoThreadingModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "No Threading"
    DESCRIPTION = "Times out users who starts a thread"
    CATEGORY = "Moderation"
    SETTINGS = [
        ModuleSetting(
            key="moderation_action",
            label="Moderation action to apply",
            type="options",
            required=True,
            default="Timeout",
            options=["Delete", "Timeout"],
        ),
        ModuleSetting(
            key="timeout_duration",
            label="Timeout duration (if moderation action is timeout)",
            type="number",
            required=True,
            placeholder="",
            default=60,
            constraints={"min_value": 1, "max_value": 1209600},
        ),
        ModuleSetting(
            key="enable_in_online_chat", label="Enabled in online chat", type="boolean", required=True, default=True
        ),
        ModuleSetting(
            key="enable_in_offline_chat", label="Enabled in offline chat", type="boolean", required=True, default=True
        ),
        ModuleSetting(
            key="timeout_reason",
            label="Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="no threading allowed",
            constraints={},
        ),
    ]

    def on_message(self, source: User, message: str, emote_instances: list[EmoteInstance], msg_id: str, tags, **rest) -> bool:
        if self.bot is None:
            log.warning("Module bot is None")
            return True

        if source.moderator is True:
            return True

        if self.bot.is_online and not self.settings["enable_in_online_chat"]:
            return True

        if not self.bot.is_online and not self.settings["enable_in_offline_chat"]:
            return True

        if "reply-thread-parent-msg-id" in tags:
            self.bot.delete_or_timeout(
                source,
                self.settings["moderation_action"],
                msg_id,
                self.settings["timeout_duration"],
                self.settings["timeout_reason"],
                disable_warnings=True,
            )

            return False

        return True

    def enable(self, bot: Optional[Bot]) -> None:
        HandlerManager.add_handler("on_message", self.on_message, priority=150, run_if_propagation_stopped=True)

    def disable(self, bot: Optional[Bot]) -> None:
        HandlerManager.remove_handler("on_message", self.on_message)
