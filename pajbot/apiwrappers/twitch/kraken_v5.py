import logging

from pajbot.apiwrappers.response_cache import ListSerializer
from pajbot.apiwrappers.twitch.base import BaseTwitchAPI
from pajbot.models.emote import Emote

log = logging.getLogger(__name__)


class TwitchKrakenV5API(BaseTwitchAPI):
    authorization_header_prefix = "OAuth"

    def __init__(self, client_credentials, redis):
        super().__init__(base_url="https://api.twitch.tv/kraken/", redis=redis)
        self.session.headers["Accept"] = "application/vnd.twitchtv.v5+json"
        self.client_credentials = client_credentials

    @property
    def default_authorization(self):
        return self.client_credentials

    def fetch_global_emotes(self):
        # circular import prevention
        from pajbot.managers.emote import EmoteManager

        resp = self.get("/chat/emoticon_images", params={"emotesets": "0"})
        return [EmoteManager.twitch_emote(str(data["id"]), data["code"]) for data in resp["emoticon_sets"]["0"]]

    def get_global_emotes(self, force_fetch=False):
        return self.cache.cache_fetch_fn(
            redis_key="api:twitch:kraken:v5:global-emotes",
            fetch_fn=lambda: self.fetch_global_emotes(),
            serializer=ListSerializer(Emote),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )
