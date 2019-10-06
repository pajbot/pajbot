import logging

from datetime import timedelta

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class MaxMsgLengthModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Maximum message length"
    DESCRIPTION = "Times out users who post messages that contain too many characters."
    CATEGORY = "Filter"
    SETTINGS = [
        ModuleSetting(
            key="max_msg_length",
            label="Max message length (Online chat)",
            type="number",
            required=True,
            placeholder="",
            default=400,
            constraints={"min_value": 40, "max_value": 1000},
        ),
        ModuleSetting(
            key="max_msg_length_offline",
            label="Max message length (Offline chat)",
            type="number",
            required=True,
            placeholder="",
            default=400,
            constraints={"min_value": 40, "max_value": 1000},
        ),
        ModuleSetting(
            key="timeout_length",
            label="Timeout length",
            type="number",
            required=True,
            placeholder="Timeout length in seconds",
            default=120,
            constraints={"min_value": 30, "max_value": 3600},
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
    ]

    def on_message(self, source, message, whisper, **rest):
        if whisper:
            return
        if source.level >= self.settings["bypass_level"] or source.moderator:
            return

        if self.bot.is_online:
            if len(message) > self.settings["max_msg_length"]:
                duration, punishment = self.bot.timeout_warn(
                    source, self.settings["timeout_length"], reason="Message too long"
                )
                """ We only send a notification to the user if he has spent more than
                one hour watching the stream. """
                if duration > 0 and source.time_in_chat_online >= timedelta(hours=1):
                    self.bot.whisper(source, f"You have been {punishment} because your message was too long.")
                return False
        else:
            if len(message) > self.settings["max_msg_length_offline"]:
                duration, punishment = self.bot.timeout_warn(
                    source, self.settings["timeout_length"], reason="Message too long"
                )
                """ We only send a notification to the user if he has spent more than
                one hour watching the stream. """
                if duration > 0 and source.time_in_chat_online >= timedelta(hours=1):
                    self.bot.whisper(source, f"You have been {punishment} because your message was too long.")
                return False

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message, priority=100)

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)
