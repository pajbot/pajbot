import logging

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class CaseCheckerModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Case Checker"
    DESCRIPTION = "Times out users who post messages that contain lowercase/uppercase letters."
    CATEGORY = "Moderation"
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
        ModuleSetting(
            key="uppercase_timeout_reason",
            label="Uppercase Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="no uppercase characters allowed",
            constraints={},
        ),
        ModuleSetting(
            key="lowercase_timeout_reason",
            label="Lowercase Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="NO LOWERCASE CHARACTERS ALLOWED",
            constraints={},
        ),
        ModuleSetting(
            key="timeout_percentage_toggle",
            label="Timeout any message that contains a percentage of uppercase letters",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="percentage_timeout_reason",
            label="Percentage Timeout Reason",
            type="text",
            required=True,
            placeholder="",
            default="Too many uppercase letters",
            constraints={},
        ),
        ModuleSetting(
            key="max_amount",
            label="Maximum amount allowed in a message",
            type="number",
            required=True,
            placeholder="",
            default=50,
            constraints={},
        ),
        ModuleSetting(
            key="min_characters",
            label="Minimum amount before checking for excessive use of uppercase letters",
            type="number",
            required=True,
            placeholder="",
            default=8,
            constraints={},
        ),
        ModuleSetting(
            key="max_percent",
            label="Maximum percent of uppercase letters allowed in message",
            type="number",
            required=True,
            placeholder="",
            default=60,
            constraints={"min_value": 0, "max_value": 100},
        ),
    ]

    def on_message(self, source, message, **rest):
        if source.level >= self.settings["bypass_level"] or source.moderator is True:
            return True

        if self.settings["online_chat_only"] and not self.bot.is_online:
            return True

        if self.settings["timeout_uppercase"] and any(c.isupper() for c in message):
            self.bot.timeout(
                source, self.settings["timeout_duration"], reason=self.settings["uppercase_timeout_reason"], once=True
            )
            return False

        if self.settings["timeout_lowercase"] and any(c.islower() for c in message):
            self.bot.timeout(
                source, self.settings["timeout_duration"], reason=self.settings["lowercase_timeout_reason"], once=True
            )
            return False
        # The module will check first if the amount of uppercase letters in a message is more than the max set amount
        # If not, the module will figure out the percentage of uppercase letters in the message
        # If the percentage is higher than the max percent, then the user will be timed out
        amount_capitals = sum(1 for c in message if c.isupper())
        if self.settings["timeout_percentage_toggle"] is True:
            if amount_capitals >= self.settings["max_amount"]:
                self.bot.timeout(
                    source, self.settings["timeout_duration"], reason=self.settings["percentage_timeout_reason"]
                )
            elif (
                amount_capitals >= self.settings["min_characters"]
                and (amount_capitals / len(message)) * 100 >= self.settings["max_percent"]
            ):
                self.bot.timeout(
                    source, self.settings["timeout_duration"], reason=self.settings["percentage_timeout_reason"]
                )
                return False

        return True

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message)

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)
