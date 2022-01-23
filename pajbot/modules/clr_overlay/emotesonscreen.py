import logging
import random

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule, ModuleSetting
from pajbot.modules.clr_overlay import CLROverlayModule

log = logging.getLogger(__name__)


class EmotesOnScreenModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Emotes on Screen"
    DESCRIPTION = "Shows one or more emotes on screen per message"
    CATEGORY = "Feature"
    PARENT_MODULE = CLROverlayModule
    SETTINGS = [
        ModuleSetting(
            key="emote_whitelist",
            label="Whitelisted emotes (separate by spaces). Leave empty to use the blacklist.",
            type="text",
            required=True,
            placeholder="i.e. Kappa Keepo PogChamp KKona",
            default="",
        ),
        ModuleSetting(
            key="emote_blacklist",
            label="Blacklisted emotes (separate by spaces). Leave empty to allow all emotes.",
            type="text",
            required=True,
            placeholder="i.e. Kappa Keepo PogChamp KKona",
            default="",
        ),
        ModuleSetting(
            key="emote_opacity",
            label="Emote opacity (in percent)",
            type="number",
            required=True,
            placeholder="",
            default=100,
            constraints={"min_value": 0, "max_value": 100},
        ),
        ModuleSetting(
            key="max_emotes_per_message",
            label="Maximum number of emotes per message that may appear on the screen. "
            "Set to 500 for practically unlimited.",
            type="number",
            required=True,
            placeholder="",
            default=1,
            constraints={"min_value": 0, "max_value": 500},
        ),
        ModuleSetting(
            key="emote_persistence_time",
            label="Time in milliseconds until emotes disappear on screen",
            type="number",
            required=True,
            placeholder="",
            default=5000,
            constraints={"min_value": 500, "max_value": 60000},
        ),
        ModuleSetting(
            key="emote_onscreen_scale",
            label="Scale emotes onscreen by this factor (100 = normal size)",
            type="number",
            required=True,
            placeholder="",
            default=100,
            constraints={"min_value": 0, "max_value": 100000},
        ),
    ]

    def is_emote_allowed(self, emote_code):
        if len(self.settings["emote_whitelist"].strip()) > 0:
            return emote_code in self.settings["emote_whitelist"]

        return emote_code not in self.settings["emote_blacklist"]

    def on_message(self, emote_instances, whisper, **rest):
        if whisper:
            return

        # filter out disallowed emotes
        emotes = [e.emote for e in emote_instances if self.is_emote_allowed(e.emote.code)]

        sample_size = min(len(emotes), self.settings["max_emotes_per_message"])
        sent_emotes = random.sample(emotes, sample_size)

        if len(sent_emotes) <= 0:
            return

        self.bot.websocket_manager.emit(
            "new_emotes",
            {
                "emotes": [e.jsonify() for e in sent_emotes],
                "opacity": self.settings["emote_opacity"],
                "persistence_time": self.settings["emote_persistence_time"],
                "scale": self.settings["emote_onscreen_scale"],
            },
        )

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message)

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)
