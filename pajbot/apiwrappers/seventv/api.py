from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import logging

from pajbot.apiwrappers.base import BaseAPI
from pajbot.apiwrappers.response_cache import ListSerializer
from pajbot.models.emote import Emote

from requests import HTTPError

from . import model

if TYPE_CHECKING:
    from pajbot.managers.redis import RedisType

log = logging.getLogger(__name__)


class SevenTVAPI(BaseAPI):
    def __init__(self, redis: Optional[RedisType]) -> None:
        super().__init__(base_url="https://7tv.io/v3/", redis=redis)

    @staticmethod
    def parse_emotes(api_emotes: List[model.Emote]) -> List[Emote]:
        def get_emote_urls(host: model.Host) -> Tuple[Dict[str, str], int, int]:
            urls = {}
            base_url = "https:" + host.url
            emote_size = 1
            max_width = 0
            max_height = 0
            for file in host.files:
                if file.format == "WEBP":
                    name = file.name
                    urls[str(emote_size)] = f"{base_url}/{name}"
                    if file.width > max_width:
                        max_width = file.width
                    if file.height > max_height:
                        max_height = file.height
                    emote_size += 1

            if len(urls) == 0 or max_width <= 0 or max_height <= 0:
                raise ValueError("No file in WEBP format for this emote")
            return (urls, max_width, max_height)

        emotes = []
        for active_emote in api_emotes:
            (urls, max_width, max_height) = get_emote_urls(active_emote.data.host)
            emotes.append(
                Emote(
                    code=active_emote.name,
                    provider="7tv",
                    id=active_emote.id,
                    max_width=max_width,
                    max_height=max_height,
                    urls=urls,
                )
            )
        return emotes

    def fetch_global_emotes(self) -> List[Emote]:
        """Returns a list of global 7TV emotes in the standard Emote format."""
        raw_response = self.get_response("emote-sets/global")

        response = model.GetEmoteSetResponseSchema().loads(raw_response.text)

        # This assert only works since we don't set many=True
        assert isinstance(response, model.GetEmoteSetResponse)

        return self.parse_emotes(response.emotes)

    def get_global_emotes(self, force_fetch: bool = False) -> List[Emote]:
        return self.cache.cache_fetch_fn(
            redis_key="api:7tv:global-emotes",
            fetch_fn=lambda: self.fetch_global_emotes(),
            serializer=ListSerializer(Emote),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )

    def fetch_channel_emotes(self, channel_id: str) -> List[Emote]:
        """Returns a list of channel-specific 7TV emotes in the standard Emote format."""
        try:
            raw_response = self.get_response(f"users/twitch/{channel_id}")
        except HTTPError as e:
            if e.response.status_code == 404:
                # user does not have a 7TV account
                return []

            raise e

        response = model.GetTwitchUserResponseSchema().loads(raw_response.text)

        # This assert only works since we don't set many=True
        assert isinstance(response, model.GetTwitchUserResponse)

        if response.emote_set is None:
            log.debug("Streamer has a 7TV account but no emote set selected")
            return []

        if response.emote_set.emotes is None:
            log.debug("Streamer has a 7TV account, an emote set created, but no emotes in that emote set")
            return []

        return self.parse_emotes(response.emote_set.emotes)

    def get_channel_emotes(self, channel_id: str, force_fetch: bool = False) -> List[Emote]:
        return self.cache.cache_fetch_fn(
            redis_key=f"api:7tv:channel-emotes:{channel_id}",
            fetch_fn=lambda: self.fetch_channel_emotes(channel_id),
            serializer=ListSerializer(Emote),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )
