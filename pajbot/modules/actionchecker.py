import logging

from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.managers.handler import HandlerManager

log = logging.getLogger(__name__)


class ActionCheckerModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Action Command Moderation"
    DESCRIPTION = "Dis/allows messages who use the /me command."
    CATEGORY = "Moderation"
    SETTINGS = [
        ModuleSetting(
            key="only_allow_action_messages",
            label="Only allow /me messages",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="allow_timeout_reason",
            label="Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="Lack of /me usage",
            constraints={},
        ),
        ModuleSetting(
            key="disallow_action_messages",
            label="Disallow /me messages",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="disallow_timeout_reason",
            label="Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="No /me usage allowed!",
            constraints={},
        ),
        ModuleSetting(
            key="enabled_by_stream_status",
            label="Enable moderation of the /me command when the stream is:",
            type="options",
            required=True,
            default="Offline and Online",
            options=["Online Only", "Offline Only", "Offline and Online"],
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
            default=30,
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
    ]

    def delete_or_timeout(self, user, msg_id, reason):
        if self.settings["moderation_action"] == "Delete":
            self.bot.delete_message(msg_id)
        elif self.settings["moderation_action"] == "Timeout":
            self.bot.timeout(user, self.settings["timeout_length"], reason, once=True)

    def on_message(self, source, message, event, msg_id, **rest):
        if self.settings["enabled_by_stream_status"] == "Online Only" and not self.bot.is_online:
            return

        if self.settings["enabled_by_stream_status"] == "Offline Only" and self.bot.is_online:
            return

        if source.level >= self.settings["bypass_level"] or source.moderator is True:
            return

        if event.type == "action" and self.settings["disallow_action_messages"] is True:
            self.delete_or_timeout(source, msg_id, self.settings["disallow_timeout_reason"])
            return False

        if event.type != "action" and self.settings["only_allow_action_messages"] is True:
            self.delete_or_timeout(source, msg_id, self.settings["allow_timeout_reason"])
            return False

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message, priority=150, run_if_propagation_stopped=True)

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)
