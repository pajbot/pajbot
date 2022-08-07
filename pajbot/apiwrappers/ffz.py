from typing import List

from pajbot.apiwrappers.base import BaseAPI
from pajbot.apiwrappers.response_cache import ListSerializer
from pajbot.models.emote import Emote

from requests import HTTPError


class FFZAPI(BaseAPI):
    def __init__(self, redis) -> None:
        super().__init__(base_url="https://api.frankerfacez.com/v1/", redis=redis)

    @staticmethod
    def parse_sets(emote_sets) -> List[Emote]:
        emotes = []
        for emote_set in emote_sets.values():
            for emote in emote_set["emoticons"]:
                # FFZ returns relative URLs (e.g. //cdn.frankerfacez.com/...)
                # so we fill in the scheme if it's missing :)
                urls = {size: FFZAPI.fill_in_url_scheme(url) for size, url in emote["urls"].items()}
                emotes.append(
                    Emote(
                        code=emote["name"],
                        provider="ffz",
                        id=str(emote["id"]),
                        urls=urls,
                        max_width=emote["width"] * 4,
                        max_height=emote["height"] * 4,
                    )
                )

        return emotes

    def fetch_global_emotes(self) -> List[Emote]:
        """Returns a list of global FFZ emotes in the standard Emote format."""
        response = self.get("/set/global")

        # FFZ returns a number of global sets but only a subset of them should be available
        # in all channels, those are available under "default_sets", e.g. a list of set IDs like this:
        # [ 3, 6, 7, 14342 ]
        global_set_ids = response["default_sets"]
        global_sets = {str(set_id): response["sets"][str(set_id)] for set_id in global_set_ids}

        return self.parse_sets(global_sets)

    def get_global_emotes(self, force_fetch=False) -> List[Emote]:
        return self.cache.cache_fetch_fn(
            redis_key="api:ffz:global-emotes",
            fetch_fn=lambda: self.fetch_global_emotes(),
            serializer=ListSerializer(Emote),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )

    def fetch_channel_emotes(self, channel_name):
        """Returns a list of channel-specific FFZ emotes in the standard Emote format."""
        try:
            response = self.get(["room", channel_name])
        except HTTPError as e:
            if e.response.status_code == 404:
                # user does not have any FFZ emotes
                return []

            raise e

        return self.parse_sets(response["sets"])

    def get_channel_emotes(self, channel_name, force_fetch=False):
        return self.cache.cache_fetch_fn(
            redis_key=f"api:ffz:channel-emotes:{channel_name}",
            fetch_fn=lambda: self.fetch_channel_emotes(channel_name),
            serializer=ListSerializer(Emote),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )
