import logging

from pajbot.emoji import ALL_EMOJI
from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class EmoteTimeoutModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Emote timeout"
    DESCRIPTION = "Times out users who post emoji or Twitch, BTTV or FFZ emotes"
    CATEGORY = "Filter"
    SETTINGS = [
        ModuleSetting(
            key="timeout_twitch", label="Timeout any Twitch emotes", type="boolean", required=True, default=False
        ),
        ModuleSetting(key="timeout_ffz", label="Timeout any FFZ emotes", type="boolean", required=True, default=False),
        ModuleSetting(
            key="timeout_bttv", label="Timeout any BTTV emotes", type="boolean", required=True, default=False
        ),
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
            constraints={"min_value": 3, "max_value": 120},
        ),
        ModuleSetting(
            key="enable_in_online_chat", label="Enabled in online chat", type="boolean", required=True, default=True
        ),
        ModuleSetting(
            key="enable_in_offline_chat", label="Enabled in offline chat", type="boolean", required=True, default=True
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

        if self.settings["timeout_twitch"] and any(e.emote.provider == "twitch" for e in emote_instances):
            self.delete_or_timeout(source, msg_id, "No Twitch emotes allowed")
            return False

        if self.settings["timeout_ffz"] and any(e.emote.provider == "ffz" for e in emote_instances):
            self.delete_or_timeout(source, msg_id, "No FFZ emotes allowed")
            return False

        if self.settings["timeout_bttv"] and any(e.emote.provider == "bttv" for e in emote_instances):
            self.delete_or_timeout(source, msg_id, "No BTTV emotes allowed")
            return False

        if self.settings["timeout_emoji"] and any(emoji in message for emoji in ALL_EMOJI):
            self.delete_or_timeout(source, msg_id, "No emoji allowed")
            return False

        return True

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message)

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)
