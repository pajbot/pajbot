import logging

from pajbot.apiwrappers.twitch_common import BaseTwitchKrakenAPI

log = logging.getLogger(__name__)


class KrakenV5TwitchApi(BaseTwitchKrakenAPI):
    def __init__(self, client_id=None, oauth=None):
        super().__init__(
            "https://api.twitch.tv/kraken/", client_id, oauth, {"Accept": "application/vnd.twitchtv.v5+json"}
        )

    def get_global_emotes(self):
        # circular import prevention
        from pajbot.managers.emote import EmoteManager

        resp = self.get("/chat/emoticon_images", params={"emotesets": "0"})
        return [EmoteManager.twitch_emote(data["id"], data["code"]) for data in resp["emoticon_sets"]["0"]]
