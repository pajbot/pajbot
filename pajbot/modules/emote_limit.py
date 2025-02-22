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


class EmoteLimitModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Emote Limit"
    DESCRIPTION = "Times out users who post too many emotes"
    CATEGORY = "Moderation"
    SETTINGS = [
        ModuleSetting(
            key="max_emotes",
            label="Maximum number of emotes that can be posted",
            type="number",
            required=True,
            placeholder="",
            default=15,
            constraints={"min_value": 1, "max_value": 167},
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
            default="Too many emotes in your message",
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
            meta.add(__name__, "user is mod")
            return HandlerResponse.null()

        if self.bot.is_online and not self.settings["enable_in_online_chat"]:
            return HandlerResponse.null()

        if not self.bot.is_online and not self.settings["enable_in_offline_chat"]:
            return HandlerResponse.null()

        if self.settings["allow_subs_to_bypass"] and source.subscriber is True:
            return HandlerResponse.null()

        if len(emote_instances) > self.settings["max_emotes"]:
            res = HandlerResponse()
            res.delete_or_timeout(
                source.id,
                self.settings["moderation_action"],
                msg_id,
                self.settings["timeout_duration"],
                reason=self.settings["timeout_reason"],
                disable_warnings=self.settings["disable_warnings"],
            )
            return res

        return HandlerResponse.null()

    def enable(self, bot: Optional[Bot]) -> None:
        if bot:
            HandlerManager.register_on_message(self.on_message, priority=150)

    def disable(self, bot: Optional[Bot]) -> None:
        if bot:
            HandlerManager.unregister_on_message(self.on_message)
