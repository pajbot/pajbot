import logging

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule, ModuleSetting

log = logging.getLogger(__name__)


class WideEmoteLimitModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Wide Emote Limit"
    DESCRIPTION = "Times out users who post too many wide 7TV or FFZ emotes"
    CATEGORY = "Moderation"
    SETTINGS = [
        ModuleSetting(
            key="max_emotes",
            label="Maximum number of wide emotes that can be posted",
            type="number",
            required=True,
            placeholder="",
            default=15,
            constraints={"min_value": 1, "max_value": 167},
        ),
        ModuleSetting(
            key="max_width",
            label="Maximum width of emotes in pixels. Emotes exceeding this width will be counted as wide",
            type="number",
            required=True,
            placeholder="",
            default=128,
            constraints={"min_value": 112, "max_value": 1000},
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
            constraints={"min_value": 1, "max_value": 1209600},
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
            default="Your message contains too many wide emotes",
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

    def on_message(self, source, message, emote_instances, msg_id, **rest):
        if source.level >= self.settings["bypass_level"] or source.moderator is True:
            return True

        if self.bot.is_online and not self.settings["enable_in_online_chat"]:
            return True

        if not self.bot.is_online and not self.settings["enable_in_offline_chat"]:
            return True
        
        if self.settings["allow_subs_to_bypass"] and source.subscriber is True:
            return True

        exceeding_emotes = [i.emote.width for i in emote_instances if i.emote.width > self.settings["max_width"]]
        if len(exceeding_emotes) > self.settings["max_emotes"]:
            self.bot.delete_or_timeout(
                source,
                self.settings["moderation_action"],
                msg_id,
                self.settings["timeout_duration"],
                self.settings["timeout_reason"],
                disable_warnings=self.settings["disable_warnings"],
                once=True,
            )

            return False

        def enable(self, bot):
            HandlerManager.add_handler("on_message", self.on_message, priority=150, run_if_propagation_stopped=True)

        def disable(self, bot):
            HandlerManager.remove_handler("on_message", self.on_message)