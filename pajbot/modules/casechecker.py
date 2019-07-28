import logging

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class CaseCheckerModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Case checker"
    DESCRIPTION = "Times out users who post messages that contain lowercase/uppercase letters."
    CATEGORY = "Filter"
    SETTINGS = [
        ModuleSetting(
            key="timeout_uppercase",
            label="Timeout any uppercase in messages",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="timeout_lowercase",
            label="Timeout any lowercase in messages",
            type="boolean",
            required=True,
            default=False,
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
            key="timeout_duration",
            label="Timeout duration",
            type="number",
            required=True,
            placeholder="",
            default=3,
            constraints={"min_value": 3, "max_value": 120},
        ),
        ModuleSetting(
            key="online_chat_only", label="Only enabled in online chat", type="boolean", required=True, default=True
        ),
    ]

    def on_message(self, source, message, **rest):
        if source.level >= self.settings["bypass_level"] or source.moderator is True:
            return True

        if self.settings["online_chat_only"] and not self.bot.is_online:
            return True

        if self.settings["timeout_uppercase"] and any(c.isupper() for c in message):
            self.bot.timeout_user_once(
                source, self.settings["timeout_duration"], reason="no uppercase characters allowed"
            )
            return False

        if self.settings["timeout_lowercase"] and any(c.islower() for c in message):
            self.bot.timeout_user_once(
                source, self.settings["timeout_duration"], reason="NO LOWERCASE CHARACTERS ALLOWED"
            )
            return False

        return True

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message)

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)
