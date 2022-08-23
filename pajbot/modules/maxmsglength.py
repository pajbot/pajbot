from __future__ import annotations

import logging

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule, ModuleSetting

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

    def on_message(self, source, message, whisper, msg_id, **rest):
        if whisper:
            return
        if source.level >= self.settings["bypass_level"] or source.moderator:
            return

        if self.bot.is_online:
            if len(message) > self.settings["max_msg_length"]:
                self.bot.delete_or_timeout(
                    source,
                    self.settings["moderation_action"],
                    msg_id,
                    self.settings["timeout_length"],
                    self.settings["timeout_reason"],
                    disable_warnings=self.settings["disable_warnings"],
                    once=True,
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
                    once=True,
                )
                return False

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message, priority=150, run_if_propagation_stopped=True)

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)
