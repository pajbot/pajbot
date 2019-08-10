from pajbot.apiwrappers.response_cache import DateTimeSerializer
from pajbot.apiwrappers.twitch.base import BaseTwitchAPI


class TwitchHelixAPI(BaseTwitchAPI):
    authorization_header_prefix = "Bearer"

    def __init__(self, redis, app_token_manager):
        super().__init__(base_url="https://api.twitch.tv/helix", redis=redis)
        self.app_token_manager = app_token_manager

    @property
    def default_authorization(self):
        return self.app_token_manager

    def fetch_user_id(self, username):
        """Fetches the twitch user ID as a string for the given twitch login name.
        If the user is not found, None is returned."""
        response = self.get("/users", {"login": username})

        # response =
        # {
        #   "data": [{
        #     "id": "44322889",
        #     "login": "dallas",
        #     "display_name": "dallas",
        #     "type": "staff",
        #     "broadcaster_type": "",
        #     "description": "Just a gamer playing games and chatting. :)",
        #     "profile_image_url": "https://static-cdn.jtvnw.net/jtv_user_pictures/dallas-profile_image-1a2c906ee2c35f12-300x300.png",
        #     "offline_image_url": "https://static-cdn.jtvnw.net/jtv_user_pictures/dallas-channel_offline_image-1a2c906ee2c35f12-1920x1080.png",
        #     "view_count": 191836881
        #   }]
        # }

        if len(response["data"]) <= 0:
            return None

        return response["data"][0]["id"]

    def get_user_id(self, username):
        """Gets the twitch user ID as a string for the given twitch login name,
        utilizing a cache or the twitch API on cache miss.
        If the user is not found, None is returned."""

        return self.cache.cache_fetch_fn(
            redis_key="api:twitch:helix:user-id:{}".format(username),
            fetch_fn=lambda: self.fetch_user_id(username),
            expiry=lambda response: 30 if response is None else 300,
        )

    def require_user_id(self, username):
        user_id = self.get_user_id(username)
        if user_id is None:
            raise ValueError("Username {} does not exist on twitch".format(username))
        return user_id

    def fetch_follow_since(self, from_id, to_id):
        response = self.get("/users/follows", {"from_id": from_id, "to_id": to_id})

        if len(response["data"]) <= 0:
            return None

        return self.parse_datetime(response["data"][0]["followed_at"])

    def get_follow_since(self, from_id, to_id):
        return self.cache.cache_fetch_fn(
            redis_key="api:twitch:helix:follow-since:{}:{}".format(from_id, to_id),
            serializer=DateTimeSerializer(),
            fetch_fn=lambda: self.fetch_follow_since(from_id, to_id),
            expiry=lambda response: 30 if response is None else 300,
        )

    def fetch_profile_image_url(self, user_id):
        response = self.get("/users", {"id": user_id})

        # response =
        # {
        #   "data": [{
        #     "id": "44322889",
        #     "login": "dallas",
        #     "display_name": "dallas",
        #     "type": "staff",
        #     "broadcaster_type": "",
        #     "description": "Just a gamer playing games and chatting. :)",
        #     "profile_image_url": "https://static-cdn.jtvnw.net/jtv_user_pictures/dallas-profile_image-1a2c906ee2c35f12-300x300.png",
        #     "offline_image_url": "https://static-cdn.jtvnw.net/jtv_user_pictures/dallas-channel_offline_image-1a2c906ee2c35f12-1920x1080.png",
        #     "view_count": 191836881
        #   }]
        # }

        if len(response["data"]) < 0:
            raise ValueError("No user with ID {} found".format(user_id))

        return response["data"][0]["profile_image_url"]
