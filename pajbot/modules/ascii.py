import logging

from pajbot.managers.handler import HandlerManager
from pajbot.modules.base import BaseModule, ModuleSetting

log = logging.getLogger(__name__)


class AsciiProtectionModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "ASCII Protection"
    DESCRIPTION = "Times out users who post messages that contain too many ASCII characters."
    CATEGORY = "Moderation"
    SETTINGS = [
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
            label="Online timeout duration, 0 = off (if moderation action is timeout)",
            type="number",
            required=True,
            placeholder="",
            default=120,
            constraints={"min_value": 0, "max_value": 1209600},
        ),
        ModuleSetting(
            key="timeout_offline",
            label="Offline Timeout duration, 0 = off (if moderation action is timeout)",
            type="number",
            required=True,
            placeholder="",
            default=60,
            constraints={"min_value": 0, "max_value": 1209600},
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

    def on_pubmsg(self, source, message, tags, **rest):
        if source.level >= self.settings["bypass_level"] or source.moderator is True:
            return

        if self.settings["moderation_action"] == "Timeout":
            if self.settings["timeout_online"] == 0 and self.bot.is_online:
                return
            if self.settings["timeout_offline"] == 0 and not self.bot.is_online:
                return

        if len(message) <= self.settings["min_msg_length"]:
            return

        if AsciiProtectionModule.check_message(message) is False:
            return

        if self.settings["moderation_action"] == "Delete":
            self.bot.delete_message(tags["id"])
        elif self.settings["disable_warnings"] is True and self.settings["moderation_action"] == "Timeout":
            self.bot.timeout(source, self.settings["timeout_length"], reason=self.settings["timeout_reason"])
        else:
            self.bot.timeout_warn(source, self.settings["timeout_length"], reason=self.settings["timeout_reason"])

        return False

    def enable(self, bot):
        HandlerManager.add_handler("on_pubmsg", self.on_pubmsg, priority=150, run_if_propagation_stopped=True)

    def disable(self, bot):
        HandlerManager.remove_handler("on_pubmsg", self.on_pubmsg)
