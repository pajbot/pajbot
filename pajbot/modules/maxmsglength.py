import logging

from datetime import timedelta

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

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
            key="whisper_timeout_reason",
            label="Whisper Timeout Reason | Available arguments: {punishment}",
            type="text",
            required=False,
            placeholder="",
            default="You have been {punishment} because your message was too long.",
            constraints={},
        ),
    ]

    def on_message(self, source, message, whisper, **rest):
        if whisper:
            return
        if source.level >= self.settings["bypass_level"] or source.moderator:
            return

        if self.bot.is_online:
            if len(message) > self.settings["max_msg_length"]:
                duration, punishment = self.bot.timeout_warn(
                    source, self.settings["timeout_length"], reason=self.settings["timeout_reason"]
                )
                """ We only send a notification to the user if he has spent more than
                one hour watching the stream. """
                if duration > 0 and source.time_in_chat_online >= timedelta(hours=1):
                    self.bot.whisper(source, self.settings["whisper_timeout_reason"].format(punishment=punishment))
                return False
        else:
            if len(message) > self.settings["max_msg_length_offline"]:
                duration, punishment = self.bot.timeout_warn(
                    source, self.settings["timeout_length"], reason=self.settings["timeout_reason"]
                )
                """ We only send a notification to the user if he has spent more than
                one hour watching the stream. """
                if duration > 0 and source.time_in_chat_online >= timedelta(hours=1):
                    self.bot.whisper(source, self.settings["whisper_timeout_reason"].format(punishment=punishment))
                return False

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message, priority=150, run_if_propagation_stopped=True)

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)
