from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Set

import logging
import random

from pajbot.managers.handler import HandlerManager
from pajbot.models.emote import EmoteInstance
from pajbot.modules import BaseModule, ModuleSetting
from pajbot.modules.clr_overlay import CLROverlayModule

if TYPE_CHECKING:
    from pajbot.bot import Bot

log = logging.getLogger(__name__)


class EmotesOnScreenModule(BaseModule):
    ID = __name__.rsplit(".", maxsplit=1)[-1]
    NAME = "Emotes on Screen"
    DESCRIPTION = "Shows one or more emotes on screen per message"
    CATEGORY = "Feature"
    PARENT_MODULE = CLROverlayModule
    SETTINGS = [
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
        ModuleSetting(
            key="emote_whitelist",
            label=CLROverlayModule.ALLOWLIST_LABEL,
            type="text",
            required=True,
            placeholder=CLROverlayModule.EMOTELIST_PLACEHOLDER_TEXT,
            default="",
        ),
        ModuleSetting(
            key="emote_blacklist",
            label=CLROverlayModule.BLOCKLIST_LABEL,
            type="text",
            required=True,
            placeholder=CLROverlayModule.EMOTELIST_PLACEHOLDER_TEXT,
            default="",
        ),
    ]

    def __init__(self, bot: Optional[Bot]) -> None:
        super().__init__(bot)

        self.allowlisted_emotes: Set[str] = set()
        self.blocklisted_emotes: Set[str] = set()

        self.parent_module: Optional[CLROverlayModule] = (
            CLROverlayModule.convert(self.bot.module_manager["clroverlay-group"]) if self.bot else None
        )

    def on_loaded(self) -> None:
        self.allowlisted_emotes = set(
            self.settings["emote_whitelist"].strip().split(" ") if self.settings["emote_whitelist"] else []
        )
        self.blocklisted_emotes = set(
            self.settings["emote_blacklist"].strip().split(" ") if self.settings["emote_blacklist"] else []
        )

    def is_emote_allowed(self, emote_code: str) -> bool:
        if len(self.allowlisted_emotes) > 0:
            return emote_code in self.allowlisted_emotes

        if len(self.blocklisted_emotes) > 0:
            return emote_code not in self.blocklisted_emotes

        if not self.parent_module:
            return True

        return self.parent_module.is_emote_allowed(emote_code)

    def on_message(self, emote_instances: List[EmoteInstance], whisper: bool, **rest: Any) -> bool:
        if whisper:
            return True

        if self.bot is None:
            log.warning("EmotesOnScreen on_message called with no bot")
            return True

        # filter out disallowed emotes
        emotes = [e.emote for e in emote_instances if self.is_emote_allowed(e.emote.code)]

        sample_size = min(len(emotes), self.settings["max_emotes_per_message"])
        sent_emotes = random.sample(emotes, sample_size)

        if len(sent_emotes) <= 0:
            return True

        self.bot.websocket_manager.emit(
            "new_emotes",
            {
                "emotes": [e.jsonify() for e in sent_emotes],
                "opacity": self.settings["emote_opacity"],
                "persistence_time": self.settings["emote_persistence_time"],
                "scale": self.settings["emote_onscreen_scale"],
            },
        )

        return True

    def enable(self, bot: Optional[Bot]) -> None:
        HandlerManager.add_handler("on_message", self.on_message)

    def disable(self, bot: Optional[Bot]) -> None:
        HandlerManager.remove_handler("on_message", self.on_message)
