from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import logging

from pajbot.managers.handler import HandlerManager, HandlerResponse, ResponseMeta
from pajbot.message_event import MessageEvent
from pajbot.models.emote import EmoteInstance, EmoteInstanceCountMap
from pajbot.models.user import User
from pajbot.modules import BaseModule, ModuleSetting

if TYPE_CHECKING:
    from pajbot.bot import Bot

log = logging.getLogger(__name__)


class WideEmoteLimitModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Wide Emote Limit"
    DESCRIPTION = "Punishes users that post too many wide 7TV, BTTV or FFZ emotes."
    PAGE_DESCRIPTION = "Users who post too many wide 7TV, BTTV or FFZ emotes will be punished by this module. Twitch does not provide emote size data, so any wide emotes provided by them will not be accounted for."
    CATEGORY = "Moderation"
    SETTINGS = [
        ModuleSetting(
            key="max_wide_emotes",
            label="Maximum number of wide emotes that can be posted",
            type="number",
            required=True,
            placeholder="",
            default=15,
            constraints={"min_value": 1, "max_value": 167},
        ),
        ModuleSetting(
            key="emote_max_width",
            label="Maximum width of emotes in pixels. Emotes exceeding this width will be counted as wide. For example: Setting this value to 130 means any emote with 131 pixels width or more will be counted as wide",
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
            key="timeout_online",
            label="Online timeout duration, 0 = off (if moderation action is timeout)",
            type="number",
            required=True,
            placeholder="",
            default=60,
            constraints={"min_value": 0, "max_value": 1209600},
        ),
        ModuleSetting(
            key="timeout_offline",
            label="Offline Timeout duration, 0 = off (if moderation action is timeout)",
            type="number",
            required=True,
            placeholder="",
            default=60,
            constraints={"min_value": 0, "max_value": 1209600},
        ),
        ModuleSetting(
            key="allow_subs_to_bypass",
            label="Allow subscribers to bypass",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="timeout_reason",
            label="Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="Too many wide emotes",
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
        if self.bot is None:
            log.warning("Module bot is None")
            return HandlerResponse.null()

        if msg_id is None:
            # Module can only handle messages from Twitch chat
            return HandlerResponse.null()

        if source.level >= self.settings["bypass_level"] or source.moderator is True:
            return HandlerResponse.null()

        if self.settings["allow_subs_to_bypass"] and source.subscriber is True:
            return HandlerResponse.null()

        if self.settings["moderation_action"] == "Timeout":
            if self.bot.is_online and self.settings["timeout_online"] == 0:
                return HandlerResponse.null()

            if not self.bot.is_online and self.settings["timeout_offline"] == 0:
                return HandlerResponse.null()

        wide_emotes = (1 for i in emote_instances if i.emote.max_width > self.settings["emote_max_width"])
        if sum(wide_emotes) > self.settings["max_wide_emotes"]:
            return HandlerResponse.do_delete_or_timeout(
                source.id,
                self.settings["moderation_action"],
                msg_id,
                self.settings["timeout_online"] if self.bot.is_online else self.settings["timeout_offline"],
                reason=self.settings["timeout_reason"],
                disable_warnings=self.settings["disable_warnings"],
            )

        return HandlerResponse.null()

    def enable(self, bot: Optional[Bot]) -> None:
        if bot:
            HandlerManager.register_on_message(self.on_message, priority=150)

    def disable(self, bot: Optional[Bot]) -> None:
        if bot:
            HandlerManager.unregister_on_message(self.on_message)
