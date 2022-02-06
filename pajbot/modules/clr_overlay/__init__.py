from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional, Set

import logging

from pajbot.modules import BaseModule
from pajbot.modules.base import ModuleSetting, ModuleType

if TYPE_CHECKING:
    from pajbot.bot import Bot

log = logging.getLogger(__name__)


class CLROverlayModule(BaseModule):
    ID = "clroverlay-group"
    NAME = "CLR Overlay"
    DESCRIPTION = "A collection of overlays that can be used in the streaming software of choice"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED

    BASE_ALLOWLIST_LABEL: str = "Allowlisted emotes (separate by spaces). Leave empty to use the blocklist."
    BASE_BLOCKLIST_LABEL: str = "Blocklisted emotes (separate by spaces). Leave empty to allow all emotes."
    ALLOWLIST_LABEL: str = f"{BASE_ALLOWLIST_LABEL} If this and the blocklist are empty, the parent module's allow and blocklist will be used."
    BLOCKLIST_LABEL: str = f"{BASE_BLOCKLIST_LABEL} If this and the allowlist are empty, the parent module's allow and blocklist will be used."

    EMOTELIST_PLACEHOLDER_TEXT: str = "e.g. Kappa Keepo PogChamp KKona"

    SETTINGS = [
        ModuleSetting(
            key="emote_allowlist",
            label=BASE_ALLOWLIST_LABEL,
            type="text",
            required=True,
            placeholder=EMOTELIST_PLACEHOLDER_TEXT,
            default="",
        ),
        ModuleSetting(
            key="emote_blocklist",
            label=BASE_BLOCKLIST_LABEL,
            type="text",
            required=True,
            placeholder=EMOTELIST_PLACEHOLDER_TEXT,
            default="",
        ),
    ]

    def __init__(self, bot: Optional[Bot]) -> None:
        super().__init__(bot)

        self.allowlisted_emotes: Set[str] = set()
        self.blocklisted_emotes: Set[str] = set()

    def on_loaded(self) -> None:
        self.allowlisted_emotes = set(
            self.settings["emote_allowlist"].strip().split(" ") if self.settings["emote_allowlist"] else []
        )
        self.blocklisted_emotes = set(
            self.settings["emote_blocklist"].strip().split(" ") if self.settings["emote_blocklist"] else []
        )

    def is_emote_allowed(self, emote_code: str) -> bool:
        if len(self.allowlisted_emotes) > 0:
            return emote_code in self.allowlisted_emotes

        return emote_code not in self.blocklisted_emotes

    @classmethod
    def convert(cls, obj: Optional[BaseModule]) -> None:
        if obj is None:
            return

        if obj is not CLROverlayModule:
            raise RuntimeError("Paraneter sent to CLROverlay.convert must be a CLROverlayModule")

        obj.__class__ = CLROverlayModule
