import logging

from pajbot.emoji import ALL_EMOJI
from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class EmoteTimeoutModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Emote Timeout"
    DESCRIPTION = "Times out users who post emoji or Twitch, BTTV, FFZ or 7TV emotes"
    CATEGORY = "Moderation"
    SETTINGS = [
        ModuleSetting(
            key="timeout_twitch", label="Timeout any Twitch emotes", type="boolean", required=True, default=False
        ),
        ModuleSetting(key="timeout_ffz", label="Timeout any FFZ emotes", type="boolean", required=True, default=False),
        ModuleSetting(
            key="timeout_bttv", label="Timeout any BTTV emotes", type="boolean", required=True, default=False
        ),
        ModuleSetting(key="timeout_7tv", label="Timeout any 7TV emotes", type="boolean", required=True, default=False),
        ModuleSetting(
            key="timeout_emoji", label="Timeout any unicode emoji", type="boolean", required=True, default=False
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
            default="Delete",
            options=["Delete", "Timeout"],
        ),
        ModuleSetting(
            key="timeout_duration",
            label="Timeout duration (if moderation action is timeout)",
            type="number",
            required=True,
            placeholder="",
            default=5,
            constraints={"min_value": 1, "max_value": 1209600},
        ),
        ModuleSetting(
            key="enable_in_online_chat", label="Enabled in online chat", type="boolean", required=True, default=True
        ),
        ModuleSetting(
            key="enable_in_offline_chat", label="Enabled in offline chat", type="boolean", required=True, default=True
        ),
        ModuleSetting(
            key="twitch_timeout_reason",
            label="Twitch Emote Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="No Twitch emotes allowed",
            constraints={},
        ),
        ModuleSetting(
            key="ffz_timeout_reason",
            label="FFZ Emote Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="No FFZ emotes allowed",
            constraints={},
        ),
        ModuleSetting(
            key="bttv_timeout_reason",
            label="BTTV Emote Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="No BTTV emotes allowed",
            constraints={},
        ),
        ModuleSetting(
            key="7tv_timeout_reason",
            label="7TV Emote Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="No 7TV emotes allowed",
            constraints={},
        ),
        ModuleSetting(
            key="emoji_timeout_reason",
            label="Emoji Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="No emoji allowed",
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

    def delete_or_timeout(self, user, msg_id, reason):
        if self.settings["moderation_action"] == "Delete":
            self.bot.delete_message(msg_id)
        elif self.settings["moderation_action"] == "Timeout":
            if self.settings["disable_warnings"] is True:
                self.bot.timeout(user, self.settings["timeout_duration"], reason, once=True)
            else:
                self.bot.timeout_warn(user, self.settings["timeout_duration"], reason, once=True)

    def on_message(self, source, message, emote_instances, msg_id, **rest):
        if source.level >= self.settings["bypass_level"] or source.moderator is True:
            return True

        if self.bot.is_online and not self.settings["enable_in_online_chat"]:
            return True

        if not self.bot.is_online and not self.settings["enable_in_offline_chat"]:
            return True

        if self.settings["timeout_twitch"] and any(e.emote.provider == "twitch" for e in emote_instances):
            self.delete_or_timeout(source, msg_id, self.settings["twitch_timeout_reason"])
            return False

        if self.settings["timeout_ffz"] and any(e.emote.provider == "ffz" for e in emote_instances):
            self.delete_or_timeout(source, msg_id, self.settings["ffz_timeout_reason"])
            return False

        if self.settings["timeout_bttv"] and any(e.emote.provider == "bttv" for e in emote_instances):
            self.delete_or_timeout(source, msg_id, self.settings["bttv_timeout_reason"])
            return False

        if self.settings["timeout_7tv"] and any(e.emote.provider == "7tv" for e in emote_instances):
            self.delete_or_timeout(source, msg_id, self.settings["7tv_timeout_reason"])
            return False

        if self.settings["timeout_emoji"] and any(emoji in message for emoji in ALL_EMOJI):
            self.delete_or_timeout(source, msg_id, self.settings["emoji_timeout_reason"])
            return False

        return True

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message, priority=150, run_if_propagation_stopped=True)

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)
