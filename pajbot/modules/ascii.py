import logging

from datetime import timedelta

from pajbot.managers.handler import HandlerManager
from pajbot.modules.base import BaseModule
from pajbot.modules.base import ModuleSetting

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
            default="Too many ASCII characters",
            constraints={},
        ),
        ModuleSetting(
            key="whisper_offenders",
            label="Send offenders a whisper explaining the timeout",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="whisper_timeout_reason",
            label="Whisper Timeout Reason | Available arguments: {punishment}",
            type="text",
            required=False,
            placeholder="",
            default="You have been {punishment} because your message contained too many ascii characters.",
            constraints={},
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
        if self.settings["enabled_by_stream_status"] == "Online Only" and not self.bot.is_online:
            return

        if self.settings["enabled_by_stream_status"] == "Offline Only" and self.bot.is_online:
            return

        if source.level >= self.settings["bypass_level"] or source.moderator is True:
            return

        if len(message) <= self.settings["min_msg_length"]:
            return

        if AsciiProtectionModule.check_message(message) is False:
            return

        if self.settings["moderation_action"] == "Delete":
            self.bot.delete_message(tags["id"])
        else:
            duration, punishment = self.bot.timeout_warn(
                source, self.settings["timeout_length"], reason=self.settings["timeout_reason"]
            )
            """ We only send a notification to the user if he has spent more than
            one hour watching the stream. """
            if self.settings["whisper_offenders"] and duration > 0 and source.time_in_chat_online >= timedelta(hours=1):
                self.bot.whisper(source, self.settings["whisper_timeout_reason"].format(punishment=punishment))

        return False

    def enable(self, bot):
        HandlerManager.add_handler("on_pubmsg", self.on_pubmsg, priority=150, run_if_propagation_stopped=True)

    def disable(self, bot):
        HandlerManager.remove_handler("on_pubmsg", self.on_pubmsg)
