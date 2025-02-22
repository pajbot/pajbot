import logging

from pajbot.managers.handler import HandlerManager, HandlerResponse, ResponseMeta
from pajbot.message_event import MessageEvent
from pajbot.models.emote import EmoteInstance, EmoteInstanceCountMap
from pajbot.models.user import User
from pajbot.modules import BaseModule, ModuleSetting

log = logging.getLogger(__name__)


class LineFarmingModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Line Farming"
    DESCRIPTION = "Keep track on the amount of lines users type in chat"
    ENABLED_DEFAULT = True
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="count_offline", label="Count lines in offline chat", type="boolean", required=True, default=False
        )
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
            return HandlerResponse.null()

        if self.bot.is_online or self.settings["count_offline"] is True:
            source.num_lines += 1

        return HandlerResponse.null()

    def enable(self, bot):
        if bot:
            HandlerManager.register_on_message(self.on_message, priority=500)

    def disable(self, bot):
        if bot:
            HandlerManager.unregister_on_message(self.on_message)
