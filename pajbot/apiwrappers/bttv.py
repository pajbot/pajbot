from requests import HTTPError

from pajbot.apiwrappers.base import BaseAPI
from pajbot.apiwrappers.response_cache import ListSerializer
from pajbot.models.emote import Emote


class BTTVAPI(BaseAPI):
    def __init__(self, redis):
        super().__init__(base_url="https://api.betterttv.net/2/", redis=redis)

    @staticmethod
    def parse_emotes(api_response_data):
        # get with default fallback
        url_template = api_response_data.get("urlTemplate", "//cdn.betterttv.net/emote/{{id}}/{{image}}")
        url_template = BTTVAPI.fill_in_url_scheme(url_template)

        def get_url(emote_hash, size):
            return url_template.replace("{{id}}", emote_hash).replace("{{image}}", size + "x")

        emotes = []
        for emote in api_response_data["emotes"]:
            emote_hash = emote["id"]
            emotes.append(
                Emote(
                    code=emote["code"],
                    provider="bttv",
                    id=emote_hash,
                    urls={"1": get_url(emote_hash, "1"), "2": get_url(emote_hash, "2"), "4": get_url(emote_hash, "3")},
                )
            )
        return emotes

    def fetch_global_emotes(self):
        """Returns a list of global BTTV emotes in the standard Emote format."""
        return self.parse_emotes(self.get("/emotes"))

    def get_global_emotes(self, force_fetch=False):
        return self.cache.cache_fetch_fn(
            redis_key="api:bttv:global-emotes",
            fetch_fn=lambda: self.fetch_global_emotes(),
            serializer=ListSerializer(Emote),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )

    def fetch_channel_emotes(self, channel_name):
        """Returns a list of channel-specific BTTV emotes in the standard Emote format."""
        try:
            response = self.get(["channels", channel_name])
        except HTTPError as e:
            if e.response.status_code == 404:
                # user does not have any BTTV emotes
                return []
            else:
                raise e
        return self.parse_emotes(response)

    def get_channel_emotes(self, channel_name, force_fetch=False):
        return self.cache.cache_fetch_fn(
            redis_key="api:bttv:channel-emotes:{}".format(channel_name),
            fetch_fn=lambda: self.fetch_channel_emotes(channel_name),
            serializer=ListSerializer(Emote),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )
