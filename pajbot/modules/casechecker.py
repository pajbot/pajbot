import logging

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule, ModuleSetting

log = logging.getLogger(__name__)


class CaseCheckerModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Case Checker"
    DESCRIPTION = "Times out users who post messages that contain lowercase/uppercase letters."
    CATEGORY = "Moderation"
    SETTINGS = [
        ModuleSetting(
            key="online_chat_only", label="Only enabled in online chat", type="boolean", required=True, default=True
        ),
        ModuleSetting(
            key="offline_chat_only", label="Only enabled in offline chat", type="boolean", required=True, default=False
        ),
        ModuleSetting(
            key="subscriber_exemption",
            label="Exempt subscribers from case-based timeouts",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="vip_exemption",
            label="Exempt VIPs from case-based timeouts",
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
            key="lowercase_timeouts", label="Enable lowercase timeouts", type="boolean", required=True, default=False
        ),
        ModuleSetting(
            key="lowercase_timeout_duration",
            label="Lowercase Timeout duration",
            type="number",
            required=True,
            placeholder="",
            default=3,
            constraints={"min_value": 1, "max_value": 1209600},
        ),
        ModuleSetting(
            key="lowercase_timeout_reason",
            label="Lowercase Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="Too many lowercase characters",
            constraints={"max_str_len": 500},
        ),
        ModuleSetting(
            key="max_lowercase",
            label="Maximum amount of lowercase characters allowed in a message.  This setting is checked prior to the percentage-based lowercase check.",
            type="number",
            required=True,
            placeholder="",
            default=50,
            constraints={"min_value": 0, "max_value": 500},
        ),
        ModuleSetting(
            key="min_lowercase_characters",
            label="Minimum amount of lowercase characters before checking for a percentage",
            type="number",
            required=True,
            placeholder="",
            default=8,
            constraints={"min_value": 0, "max_value": 500},
        ),
        ModuleSetting(
            key="lowercase_percentage",
            label="Maximum percent of lowercase letters allowed in message",
            type="number",
            required=True,
            placeholder="",
            default=60,
            constraints={"min_value": 0, "max_value": 100},
        ),
        ModuleSetting(
            key="uppercase_timeouts", label="Enable uppercase timeouts", type="boolean", required=True, default=False
        ),
        ModuleSetting(
            key="uppercase_timeout_duration",
            label="Uppercase Timeout duration",
            type="number",
            required=True,
            placeholder="",
            default=3,
            constraints={"min_value": 1, "max_value": 1209600},
        ),
        ModuleSetting(
            key="uppercase_timeout_reason",
            label="Uppercase Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="Too many uppercase characters",
            constraints={"max_str_len": 500},
        ),
        ModuleSetting(
            key="max_uppercase",
            label="Maximum amount of uppercase characters allowed in a message. This setting is checked prior to the percentage-based uppercase check.",
            type="number",
            required=True,
            placeholder="",
            default=50,
            constraints={"min_value": 0, "max_value": 500},
        ),
        ModuleSetting(
            key="min_uppercase_characters",
            label="Minimum amount of uppercase characters before checking for a percentage",
            type="number",
            required=True,
            placeholder="",
            default=8,
            constraints={"min_value": 0, "max_value": 500},
        ),
        ModuleSetting(
            key="uppercase_percentage",
            label="Maximum percent of uppercase letters allowed in message",
            type="number",
            required=True,
            placeholder="",
            default=60,
            constraints={"min_value": 0, "max_value": 100},
        ),
        ModuleSetting(
            key="disable_warnings",
            label="Disable warning timeouts",
            type="boolean",
            required=True,
            default=False,
        ),
    ]

    def on_message(self, source, message, **rest):
        if source.level >= self.settings["bypass_level"] or source.moderator is True:
            return True

        if (self.settings["online_chat_only"] and not self.bot.is_online) or (
            self.settings["offline_chat_only"] and self.bot.is_online
        ):
            return True

        if self.settings["subscriber_exemption"] and source.subscriber is True:
            return True

        if self.settings["vip_exemption"] and source.vip is True:
            return True

        amount_lowercase = sum(1 for c in message if c.islower())
        if self.settings["lowercase_timeouts"] is True:
            if amount_lowercase >= self.settings["max_lowercase"]:
                if self.settings["disable_warnings"] is True:
                    self.bot.timeout(
                        source,
                        self.settings["lowercase_timeout_duration"],
                        reason=self.settings["lowercase_timeout_reason"],
                        once=True,
                    )
                else:
                    self.bot.timeout_warn(
                        source,
                        self.settings["lowercase_timeout_duration"],
                        reason=self.settings["lowercase_timeout_reason"],
                        once=True,
                    )
                return False

            if (
                amount_lowercase >= self.settings["min_lowercase_characters"]
                and (amount_lowercase / len(message)) * 100 >= self.settings["lowercase_percentage"]
            ):
                if self.settings["disable_warnings"] is True:
                    self.bot.timeout(
                        source,
                        self.settings["lowercase_timeout_duration"],
                        reason=self.settings["lowercase_timeout_reason"],
                        once=True,
                    )
                else:
                    self.bot.timeout_warn(
                        source,
                        self.settings["lowercase_timeout_duration"],
                        reason=self.settings["lowercase_timeout_reason"],
                        once=True,
                    )
                return False

        amount_uppercase = sum(1 for c in message if c.isupper())
        if self.settings["uppercase_timeouts"] is True:
            if amount_lowercase >= self.settings["max_uppercase"]:
                if self.settings["disable_warnings"] is True:
                    self.bot.timeout(
                        source,
                        self.settings["uppercase_timeout_duration"],
                        reason=self.settings["uppercase_timeout_reason"],
                        once=True,
                    )
                else:
                    self.bot.timeout_warn(
                        source,
                        self.settings["uppercase_timeout_duration"],
                        reason=self.settings["uppercase_timeout_reason"],
                        once=True,
                    )
                return False

            if (
                amount_uppercase >= self.settings["min_uppercase_characters"]
                and (amount_lowercase / len(message)) * 100 >= self.settings["uppercase_percentage"]
            ):
                if self.settings["disable_warnings"] is True:
                    self.bot.timeout(
                        source,
                        self.settings["uppercase_timeout_duration"],
                        reason=self.settings["uppercase_timeout_reason"],
                        once=True,
                    )
                else:
                    self.bot.timeout_warn(
                        source,
                        self.settings["uppercase_timeout_duration"],
                        reason=self.settings["uppercase_timeout_reason"],
                        once=True,
                    )
                return False

        return True

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message, priority=150, run_if_propagation_stopped=True)

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)
