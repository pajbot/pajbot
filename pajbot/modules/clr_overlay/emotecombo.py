from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

import logging

from pajbot.managers.handler import HandlerManager, HandlerResponse, ResponseMeta
from pajbot.message_event import MessageEvent
from pajbot.models.emote import Emote, EmoteInstance, EmoteInstanceCountMap
from pajbot.models.user import User
from pajbot.modules import BaseModule
from pajbot.modules.base import ModuleSetting
from pajbot.modules.clr_overlay import CLROverlayModule

if TYPE_CHECKING:
    from pajbot.bot import Bot

log = logging.getLogger(__name__)


class EmoteComboModule(BaseModule):
    ID = __name__.rsplit(".", maxsplit=1)[-1]
    NAME = "Emote Combos"
    DESCRIPTION = "Shows emote combos on the CLR pajbot overlay"
    CATEGORY = "Feature"
    PARENT_MODULE = CLROverlayModule
    SETTINGS = [
        ModuleSetting(
            key="min_emote_combo",
            label="Minimum number of emotes required to trigger the combo",
            type="number",
            required=True,
            placeholder="",
            default=5,
            constraints={"min_value": 2, "max_value": 100},
        ),
        ModuleSetting(
            key="emote_allowlist",
            label=CLROverlayModule.ALLOWLIST_LABEL,
            type="text",
            required=True,
            placeholder=CLROverlayModule.EMOTELIST_PLACEHOLDER_TEXT,
            default="",
        ),
        ModuleSetting(
            key="emote_blocklist",
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

        self.emote_count: int = 0
        self.current_emote: Optional[Emote] = None

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

        if len(self.blocklisted_emotes) > 0:
            return emote_code not in self.blocklisted_emotes

        if self.parent_module is None:
            return True

        # Override the parent module type since we 100% know it
        assert isinstance(self.parent_module, CLROverlayModule)

        return self.parent_module.is_emote_allowed(emote_code)

    def inc_emote_count(self) -> None:
        if self.bot is None:
            log.warning("EmoteCombo inc_emote_count called when bot is none")
            return

        assert self.current_emote is not None

        self.emote_count += 1

        if self.emote_count >= self.settings["min_emote_combo"]:
            self.bot.websocket_manager.emit(
                "emote_combo", {"emote": self.current_emote.jsonify(), "count": self.emote_count}
            )

    def reset(self) -> None:
        self.emote_count = 0
        self.current_emote = None

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
        if is_whisper:
            return HandlerResponse.null()

        # Check if the message contains exactly one unique emote
        num_unique_emotes = len(emote_counts)
        if num_unique_emotes != 1:
            self.reset()
            return HandlerResponse.null()

        new_emote = emote_instances[0].emote
        new_emote_code = new_emote.code

        if self.is_emote_allowed(new_emote_code) is False:
            self.reset()
            return HandlerResponse.null()

        # if there is currently a combo...
        if self.current_emote is not None:
            # and this emote is not equal to the combo emote...
            if self.current_emote.code != new_emote_code:
                # The emote of this message is not the one we were previously counting, reset.
                # We do not stop.
                # We start counting this emote instead.
                self.reset()

        if self.current_emote is None:
            self.current_emote = new_emote

        self.inc_emote_count()
        return HandlerResponse.null()

    def enable(self, bot: Optional[Bot]) -> None:
        HandlerManager.register_on_message(self.on_message)

    def disable(self, bot: Optional[Bot]) -> None:
        HandlerManager.unregister_on_message(self.on_message)
