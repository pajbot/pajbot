from __future__ import annotations

import logging

from pajbot.managers.handler import HandlerManager
from pajbot.models.user import User
from pajbot.modules import BaseModule, ModuleSetting

log = logging.getLogger(__name__)


class MaxMsgLengthModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Maximum Message Length"
    DESCRIPTION = "Times out users who post messages that contain too many characters."
    CATEGORY = "Moderation"
    SETTINGS = [
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

    def _perform_timeout(self, user: User, timeout_length: int, timeout_reason: str, disable_warnings: bool) -> None:
        if self.bot is None:
            log.warning("Bot is none in Maximum Message Length module _perform_timeout, this should never happen")
            return

        if disable_warnings is True:
            self.bot.timeout(user, timeout_length, reason=timeout_reason)
        else:
            self.bot.timeout_warn(user, timeout_length, reason=timeout_reason)

    def on_message(self, source, message, whisper, **rest):
        if whisper:
            return
        if source.level >= self.settings["bypass_level"] or source.moderator:
            return

        if self.bot.is_online:
            if len(message) > self.settings["max_msg_length"]:
                self._perform_timeout(
                    source,
                    self.settings["timeout_length"],
                    self.settings["timeout_reason"],
                    self.settings["disable_warnings"],
                )
                return False
        else:
            if len(message) > self.settings["max_msg_length_offline"]:
                self._perform_timeout(
                    source,
                    self.settings["timeout_length"],
                    self.settings["timeout_reason"],
                    self.settings["disable_warnings"],
                )
                return False

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message, priority=150, run_if_propagation_stopped=True)

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)
