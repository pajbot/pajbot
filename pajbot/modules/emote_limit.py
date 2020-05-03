import logging

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class EmoteLimitModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Emote Limit"
    DESCRIPTION = "Times out users who post too many emotes"
    CATEGORY = "Moderation"
    SETTINGS = [
        ModuleSetting(
            key="max_emotes",
            label="Maximum number of emotes that can be posted",
            type="number",
            required=True,
            placeholder="",
            default=15,
            constraints={"min_value": 1, "max_value": 40},
        ),
        ModuleSetting(
            key="bypass_level",
            label="Level to bypass module",
            type="number",
            required=True,
            placeholder="",
            default=420,
            constraints={"min_value": 100, "max_value": 1000},
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
            key="timeout_duration",
            label="Timeout duration (if moderation action is timeout)",
            type="number",
            required=True,
            placeholder="",
            default=60,
            constraints={"min_value": 3, "max_value": 3600},
        ),
        ModuleSetting(
            key="allow_subs_to_bypass",
            label="Allow subscribers to bypass",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="enable_in_online_chat", label="Enabled in online chat", type="boolean", required=True, default=True
        ),
        ModuleSetting(
            key="enable_in_offline_chat", label="Enabled in offline chat", type="boolean", required=True, default=True
        ),
        ModuleSetting(
            key="timeout_reason",
            label="Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="Too many emotes in your message",
            constraints={},
        ),
    ]

    def delete_or_timeout(self, user, msg_id, reason):
        if self.settings["moderation_action"] == "Delete":
            self.bot.delete_message(msg_id)
        elif self.settings["moderation_action"] == "Timeout":
            self.bot.timeout(user, self.settings["timeout_duration"], reason, once=True)

    def on_message(self, source, message, emote_instances, msg_id, **rest):
        if source.level >= self.settings["bypass_level"] or source.moderator is True:
            return True

        if self.bot.is_online and not self.settings["enable_in_online_chat"]:
            return True

        if not self.bot.is_online and not self.settings["enable_in_offline_chat"]:
            return True

        if self.settings["allow_subs_to_bypass"] and source.subscriber is True:
            return True

        if len(emote_instances) > self.settings["max_emotes"]:
            self.delete_or_timeout(source, msg_id, self.settings["timeout_reason"])
            return False

        return True

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message)

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)
