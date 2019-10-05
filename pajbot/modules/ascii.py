import logging

from datetime import timedelta

from pajbot.managers.handler import HandlerManager
from pajbot.modules.base import BaseModule
from pajbot.modules.base import ModuleSetting

log = logging.getLogger(__name__)


class AsciiProtectionModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Ascii Protection"
    DESCRIPTION = "Times out users who post messages that contain too many ASCII characters."
    CATEGORY = "Filter"
    SETTINGS = [
        ModuleSetting(
            key="min_msg_length",
            label="Minimum message length to be considered bad",
            type="number",
            required=True,
            placeholder="",
            default=70,
            constraints={"min_value": 20, "max_value": 1000},
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
        ModuleSetting(
            key="whisper_offenders",
            label="Send offenders a whisper explaining the timeout",
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

    def on_pubmsg(self, source, message, **rest):
        if source.level >= self.settings["bypass_level"] or source.moderator is True:
            return

        if len(message) <= self.settings["min_msg_length"]:
            return

        if AsciiProtectionModule.check_message(message) is False:
            return

        duration, punishment = self.bot.timeout_warn(
            source, self.settings["timeout_length"], reason="Too many ASCII characters"
        )

        """ We only send a notification to the user if he has spent more than
        one hour watching the stream. """
        if self.settings["whisper_offenders"] and duration > 0 and source.time_in_chat_online >= timedelta(hours=1):
            self.bot.whisper(
                source, f"You have been {punishment} because your message contained too many ascii characters."
            )

        return False

    def enable(self, bot):
        HandlerManager.add_handler("on_pubmsg", self.on_pubmsg)

    def disable(self, bot):
        HandlerManager.remove_handler("on_pubmsg", self.on_pubmsg)
