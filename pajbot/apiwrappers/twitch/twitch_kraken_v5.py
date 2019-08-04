import logging

from pajbot.apiwrappers.twitch.base import BaseTwitchApi

log = logging.getLogger(__name__)


class TwitchKrakenV5Api(BaseTwitchApi):
    authorization_header_prefix = "OAuth"

    def __init__(self, client_credentials, redis):
        super().__init__(base_url="https://api.twitch.tv/kraken/", redis=redis)
        self.session.headers["Accept"] = "application/vnd.twitchtv.v5+json"
        self.client_credentials = client_credentials

    @property
    def default_authorization(self):
        return self.client_credentials

    def get_stream_status(self, user_id):
        data = self.get(["streams", user_id])

        def rest_data_offline():
            return {
                "viewers": -1,
                "game": None,
                "title": None,
                "created_at": None,
                "followers": -1,
                "views": -1,
                "broadcast_id": None,
            }

        def rest_data_online():
            stream = data["stream"]

            return {
                "viewers": stream["viewers"],
                "game": stream["game"],
                "title": stream["channel"]["status"],
                "created_at": stream["created_at"],
                "followers": stream["channel"]["followers"],
                "views": stream["channel"]["views"],
                "broadcast_id": stream["_id"],
            }

        online = "stream" in data and data["stream"] is not None

        def rest_data():
            nonlocal online
            if online:
                return rest_data_online()
            else:
                return rest_data_offline()

        return {"online": online, **rest_data()}

    def set_game(self, user_id, game, authorization):
        self.put(["channels", user_id], json={"channel": {"game": game}}, authorization=authorization)

    def set_title(self, user_id, title, authorization):
        self.put(["channels", user_id], json={"channel": {"status": title}}, authorization=authorization)

    def get_vod_videos(self, username):
        return self.get("channels/{}/videos".format(self.quote_path_param(username)), {"broadcast_type": "archive"})

    def get_global_emotes(self):
        # circular import prevention
        from pajbot.managers.emote import EmoteManager

        resp = self.get("chat/emoticon_images", params={"emotesets": "0"})
        return [EmoteManager.twitch_emote(data["id"], data["code"]) for data in resp["emoticon_sets"]["0"]]
