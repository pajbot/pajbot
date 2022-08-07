from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

from pajbot.apiwrappers.base import BaseAPI
from pajbot.apiwrappers.response_cache import ListSerializer
from pajbot.models.emote import Emote

from requests import HTTPError

if TYPE_CHECKING:
    from pajbot.managers.redis import RedisType


class BTTVAPI(BaseAPI):
    def __init__(self, redis: RedisType) -> None:
        super().__init__(base_url="https://api.betterttv.net/3/", redis=redis)

    @staticmethod
    def parse_emotes(api_response_data: List[Dict[str, Any]]) -> List[Emote]:
        def get_url(emote_id: str, size: str) -> str:
            return f"https://cdn.betterttv.net/emote/{emote_id}/{size}x"

        emotes = []
        for emote_data in api_response_data:
            emote_id = emote_data["id"]
            emotes.append(
                Emote(
                    code=emote_data["code"],
                    provider="bttv",
                    id=emote_id,
                    urls={"1": get_url(emote_id, "1"), "2": get_url(emote_id, "2"), "4": get_url(emote_id, "3")},
                    # BTTV gives no data regarding this, but it can be assumed that this will be the emote size most of the time
                    max_width=112,
                    max_height=112,
                )
            )
        return emotes

    def fetch_global_emotes(self) -> List[Emote]:
        """Returns a list of global BTTV emotes in the standard Emote format."""
        response = self.get("/cached/emotes/global")
        return self.parse_emotes(response)

    def get_global_emotes(self, force_fetch: bool = False) -> List[Emote]:
        return self.cache.cache_fetch_fn(
            redis_key="api:bttv:global-emotes",
            fetch_fn=lambda: self.fetch_global_emotes(),
            serializer=ListSerializer(Emote),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )

    def fetch_channel_emotes(self, channel_id: str) -> List[Emote]:
        """Returns a list of channel-specific BTTV emotes in the standard Emote format."""
        try:
            response = self.get(["cached", "users", "twitch", channel_id])
        except HTTPError as e:
            if e.response.status_code == 404:
                # user does not have any BTTV emotes
                return []

            raise e
        return self.parse_emotes(response["channelEmotes"]) + self.parse_emotes(response["sharedEmotes"])

    def get_channel_emotes(self, channel_id: str, force_fetch: bool = False) -> List[Emote]:
        return self.cache.cache_fetch_fn(
            redis_key=f"api:bttv:channel-emotes:{channel_id}",
            fetch_fn=lambda: self.fetch_channel_emotes(channel_id),
            serializer=ListSerializer(Emote),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )
