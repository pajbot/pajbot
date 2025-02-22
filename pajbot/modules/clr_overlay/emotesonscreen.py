from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

import logging
import random

from pajbot.managers.handler import HandlerManager, HandlerResponse, ResponseMeta
from pajbot.message_event import MessageEvent
from pajbot.models.emote import EmoteInstance, EmoteInstanceCountMap
from pajbot.models.user import User
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

        self.allowlisted_emotes: set[str] = set()
        self.blocklisted_emotes: set[str] = set()

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

        assert isinstance(self.parent_module, CLROverlayModule)

        return self.parent_module.is_emote_allowed(emote_code)

    def _handle(self, emote_instances: list[EmoteInstance], is_whisper: bool) -> None:
        if is_whisper:
            return

        if self.bot is None:
            log.warning("EmotesOnScreen on_message called with no bot")
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

    async def on_message(
        self,
        source: User,
        message: str,
        emote_instances: list[EmoteInstance],
        emote_counts: EmoteInstanceCountMap,
        is_whisper: bool,
        urls: list[str],
        msg_id: str | None,
        event: MessageEvent,
        meta: ResponseMeta,
    ) -> HandlerResponse:
        self._handle(emote_instances, is_whisper)
        return HandlerResponse.null()

    def enable(self, bot: Optional[Bot]) -> None:
        if bot:
            HandlerManager.register_on_message(self.on_message)

    def disable(self, bot: Optional[Bot]) -> None:
        if bot:
            HandlerManager.unregister_on_message(self.on_message)
