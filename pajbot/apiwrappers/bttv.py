from requests import HTTPError

from pajbot.apiwrappers.base import BaseAPI
from pajbot.apiwrappers.response_cache import ListSerializer
from pajbot.models.emote import Emote


class BTTVAPI(BaseAPI):
    def __init__(self, redis):
        super().__init__(base_url="https://api.betterttv.net/3/", redis=redis)

    @staticmethod
    def parse_emotes(api_response_data):
        def get_url(emote_id, size):
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
                )
            )
        return emotes

    def fetch_global_emotes(self):
        """Returns a list of global BTTV emotes in the standard Emote format."""
        response = self.get("/cached/emotes/global")
        return self.parse_emotes(response)

    def get_global_emotes(self, force_fetch=False):
        return self.cache.cache_fetch_fn(
            redis_key="api:bttv:global-emotes",
            fetch_fn=lambda: self.fetch_global_emotes(),
            serializer=ListSerializer(Emote),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )

    def fetch_channel_emotes(self, channel_id):
        """Returns a list of channel-specific BTTV emotes in the standard Emote format."""
        try:
            response = self.get(["cached", "users", "twitch", channel_id])
        except HTTPError as e:
            if e.response.status_code == 404:
                # user does not have any BTTV emotes
                return []
            else:
                raise e
        return self.parse_emotes(response["channelEmotes"]) + self.parse_emotes(response["sharedEmotes"])

    def get_channel_emotes(self, channel_id, force_fetch=False):
        return self.cache.cache_fetch_fn(
            redis_key=f"api:bttv:channel-emotes:{channel_id}",
            fetch_fn=lambda: self.fetch_channel_emotes(channel_id),
            serializer=ListSerializer(Emote),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )
