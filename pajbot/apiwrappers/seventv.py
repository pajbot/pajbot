from typing import Dict, Tuple

from pajbot.apiwrappers.base import BaseAPI
from pajbot.apiwrappers.response_cache import ListSerializer
from pajbot.models.emote import Emote

from requests import HTTPError


class SevenTVAPI(BaseAPI):
    def __init__(self, redis):
        super().__init__(base_url="https://7tv.io/v3/", redis=redis)

    @staticmethod
    def parse_emotes(api_response_data):
        def get_emote_urls(host) -> Tuple[Dict[str, str], int, int]:
            urls = {}
            base_url = "https:" + host["url"]
            emote_size = 1
            max_width = 0
            max_height = 0
            for file in host["files"]:
                if file["format"] == "WEBP":
                    name = file["name"]
                    urls[str(emote_size)] = f"{base_url}/{name}"
                    if file["width"] > max_width:
                        max_width = file["width"]
                    if file["height"] > max_height:
                        max_height = file["height"]
                    emote_size += 1

            if len(urls) == 0 or max_width <= 0 or max_height <= 0:
                raise ValueError("No file in WEBP format for this emote")
            return (urls, max_width, max_height)

        emotes = []
        for active_emote in api_response_data:
            (urls, max_width, max_height) = get_emote_urls(active_emote["data"]["host"])
            emotes.append(
                Emote(
                    code=active_emote["name"],
                    provider="7tv",
                    id=active_emote["id"],
                    max_width=max_width,
                    max_height=max_height,
                    urls=urls,
                )
            )
        return emotes

    def fetch_global_emotes(self):
        """Returns a list of global 7TV emotes in the standard Emote format."""
        response = self.get("emote-sets/global")

        return self.parse_emotes(response["emotes"])

    def get_global_emotes(self, force_fetch=False):
        return self.cache.cache_fetch_fn(
            redis_key="api:7tv:global-emotes",
            fetch_fn=lambda: self.fetch_global_emotes(),
            serializer=ListSerializer(Emote),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )

    def fetch_channel_emotes(self, channel_id):
        """Returns a list of channel-specific 7TV emotes in the standard Emote format."""
        try:
            response = self.get(f"users/twitch/{channel_id}")
        except HTTPError as e:
            if e.response.status_code == 404:
                # user does not have any 7TV emotes
                return []

            raise e

        return self.parse_emotes(response["emote_set"]["emotes"])

    def get_channel_emotes(self, channel_id, force_fetch=False):
        return self.cache.cache_fetch_fn(
            redis_key=f"api:7tv:channel-emotes:{channel_id}",
            fetch_fn=lambda: self.fetch_channel_emotes(channel_id),
            serializer=ListSerializer(Emote),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )
