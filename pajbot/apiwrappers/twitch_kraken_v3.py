import logging

from requests import HTTPError

from pajbot.apiwrappers.twitch_common import BaseTwitchKrakenAPI

log = logging.getLogger(__name__)


class KrakenV3TwitchApi(BaseTwitchKrakenAPI):
    def __init__(self, client_id=None, oauth=None):
        super().__init__(
            "http://127.0.0.1:7221/kraken/", client_id, oauth, {"Accept": "application/vnd.twitchtv.v3+json"}
        )

    def get_stream_status(self, streamer):
        data = self.get("/streams/{}".format(self.quote_path_param(streamer)))

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
                "title": stream["status"],
                "created_at": stream["created_at"],
                "followers": stream["followers"],
                "views": stream["views"],
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

    def set_game(self, streamer, game):
        self.put("/channels/{}".format(self.quote_path_param(streamer)), json={"channel": {"game": game}})

    def set_title(self, streamer, title):
        self.put("/channels/{}".format(self.quote_path_param(streamer)), json={"channel": {"status": title}})

    def get_follow_relationship(self, username, streamer):
        """Returns the follow relationship between the user and a streamer.

        Returns False if `username` is not following `streamer`.
        Otherwise, return a datetime object.

        This value is cached in Redis for 2 minutes.
        """

        from pajbot.managers.redis import RedisManager

        redis = RedisManager.get()

        fr_key = "fr_{username}_{streamer}".format(username=username, streamer=streamer)
        follow_relationship = redis.get(fr_key)

        # cache hit
        if follow_relationship is not None:
            if follow_relationship == "-1":
                return False
            else:
                return self.parse_datetime(follow_relationship)

        # cache miss
        try:
            data = self.get(
                "/users/{}/follows/channels/{}".format(self.quote_path_param(username), self.quote_path_param(streamer))
            )
            created_at = data["created_at"]
            redis.setex(fr_key, time=120, value=created_at)
            return self.parse_datetime(created_at)
        except HTTPError as e:
            if e.response.status_code == 404:
                redis.setex(fr_key, time=120, value="-1")
                return False
            else:
                raise e

    def get_logo_url(self, username):
        data = self.get("/users/{}".format(self.quote_path_param(username)))
        return data["logo"]

    def get_vod_videos(self, username):
        return self.get("/channels/{}/videos".format(self.quote_path_param(username)), {"broadcast_type": "archive"})
