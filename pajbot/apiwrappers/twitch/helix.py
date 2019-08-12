import re

import logging

from pajbot.apiwrappers.response_cache import DateTimeSerializer
from pajbot.apiwrappers.twitch.base import BaseTwitchAPI


log = logging.getLogger(__name__)


class TwitchHelixAPI(BaseTwitchAPI):
    authorization_header_prefix = "Bearer"

    def __init__(self, redis, app_token_manager):
        super().__init__(base_url="https://api.twitch.tv/helix", redis=redis)
        self.app_token_manager = app_token_manager

    @property
    def default_authorization(self):
        return self.app_token_manager

    @staticmethod
    def with_pagination(after_pagination_cursor=None):
        """Returns a dict with extra query parameters based on the given pagination cursor.
        This makes a dict with the ?after=xxxx query parameter if a pagination cursor is present,
        and if no pagination cursor is present, returns an empty dict."""
        if after_pagination_cursor is None:
            return {}  # no extra query parameters
        else:
            return {"after": after_pagination_cursor}  # fetch results after this cursor

    @staticmethod
    def fetch_all_pages(page_fetch_fn, *args, **kwargs):
        """Fetch all pages using a function that returns a list of responses and a pagination cursor
        as a tuple when called with the pagination cursor as an argument."""
        pagination_cursor = None
        responses = []

        while True:
            response, pagination_cursor = page_fetch_fn(after_pagination_cursor=pagination_cursor, *args, **kwargs)

            # add this chunk's responses to the list of all responses
            responses.extend(response)

            # all pages iterated, done
            if len(response) <= 0:
                break

        return responses

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

    def fetch_login_name(self, user_id):
        """Fetches the twitch login name as a string for the given twitch login name.
        If the user is not found, None is returned."""
        response = self.get("/users", {"id": user_id})

        if len(response["data"]) <= 0:
            return None

        # response is the same as for fetch_user_id

        return response["data"][0]["login"]

    def get_login_name(self, user_id):
        """Gets the twitch login name as a string for the given twitch login name,
        utilizing a cache or the twitch API on cache miss.
        If the user is not found, None is returned."""

        return self.cache.cache_fetch_fn(
            redis_key="api:twitch:helix:login-name:{}".format(user_id),
            fetch_fn=lambda: self.fetch_login_name(user_id),
            expiry=lambda response: 30 if response is None else 300,
        )

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

    CAPITALIZED_LOGIN_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_]+$")

    def fetch_subscribers_page(self, broadcaster_id, authorization, after_pagination_cursor=None):
        """Fetch a list of subscriber usernames of a broadcaster + a pagination cursor as a tuple."""
        response = self.get(
            "/subscriptions",
            {"broadcaster_id": broadcaster_id, **self.with_pagination(after_pagination_cursor)},
            authorization=authorization,
        )

        # response =
        # {
        #   "data": [
        #     {
        #       "broadcaster_id": "123"
        #       "broadcaster_name": "test_user"
        #       "is_gift" true,
        #       "tier": "1000",
        #       "plan_name": "The Ninjas",
        #       "user_id": "123",
        #       "user_name": "snoirf",
        #     },
        #     …
        #   ],
        #   "pagination": {
        #     "cursor": "xxxx"
        #   }
        # }

        subscribers = []

        for sub_data in response["data"]:
            display_name = sub_data["user_name"]

            if self.CAPITALIZED_LOGIN_NAME_REGEX.match(display_name):
                # "normal" display name (just a capitalized variant of the login name)
                # we can directly compute the login name by lowercasing the display name
                login_name = display_name.lower()
            else:
                # hieroglyph display name, another API call is required to look up their login name from the user ID
                user_id = sub_data["user_id"]
                login_name = self.get_login_name(user_id)

                if login_name is None:
                    # user_id not found?!?!
                    # can technically happen if user deletes account in the slim moment
                    # between fetch of subscriber list and the user_id -> login_name lookup
                    log.warning(
                        "Just fetched %s (%s) to be a subscriber of %s but was not"
                        " able to locate them as a user by their ID "
                        "(user will not be counted as a subscriber)",
                        login_name,
                        user_id,
                        broadcaster_id,
                    )
                    continue

            subscribers.append(login_name)

        pagination_cursor = response["pagination"]["cursor"]

        return subscribers, pagination_cursor

    def fetch_all_subscribers(self, broadcaster_id, authorization):
        """Fetch a list of all subscriber usernames of a broadcaster."""
        return self.fetch_all_pages(self.fetch_subscribers_page, broadcaster_id, authorization)
