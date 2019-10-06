import logging
import time

from datetime import datetime, timezone

import math
from requests import HTTPError

from pajbot import utils
from pajbot.apiwrappers.response_cache import DateTimeSerializer
from pajbot.apiwrappers.twitch.base import BaseTwitchAPI
from pajbot.models.user import UserBasics
from pajbot.utils import iterate_in_chunks

log = logging.getLogger(__name__)


class TwitchHelixAPI(BaseTwitchAPI):
    authorization_header_prefix = "Bearer"

    def __init__(self, redis, app_token_manager):
        super().__init__(base_url="https://api.twitch.tv/helix", redis=redis)
        self.app_token_manager = app_token_manager

    @property
    def default_authorization(self):
        return self.app_token_manager

    def request(self, method, endpoint, params, headers, authorization=None, json=None):
        try:
            return super().request(method, endpoint, params, headers, authorization, json)
        except HTTPError as e:
            if e.response.status_code == 429:
                # retry once after rate limit resets...
                rate_limit_reset = datetime.fromtimestamp(int(e.response.headers["Ratelimit-Reset"]), tz=timezone.utc)
                time_to_wait = rate_limit_reset - utils.now()
                time.sleep(math.ceil(time_to_wait.total_seconds()))
                return super().request(method, endpoint, params, headers, authorization, json)
            else:
                raise e

    @staticmethod
    def _with_pagination(after_pagination_cursor=None):
        """Returns a dict with extra query parameters based on the given pagination cursor.
        This makes a dict with the ?after=xxxx query parameter if a pagination cursor is present,
        and if no pagination cursor is present, returns an empty dict."""
        if after_pagination_cursor is None:
            return {}  # no extra query parameters
        else:
            return {"after": after_pagination_cursor}  # fetch results after this cursor

    @staticmethod
    def _fetch_all_pages(page_fetch_fn, *args, **kwargs):
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

    def _fetch_user_data_by_login(self, login):
        response = self.get("/users", {"login": login})

        if len(response["data"]) <= 0:
            return None

        return response["data"][0]

    def _fetch_user_data_by_id(self, user_id):
        response = self.get("/users", {"id": user_id})

        if len(response["data"]) <= 0:
            return None

        return response["data"][0]

    def _get_user_data_by_login(self, login):
        return self.cache.cache_fetch_fn(
            redis_key=f"api:twitch:helix:user:by-login:{login}",
            fetch_fn=lambda: self._fetch_user_data_by_login(login),
            expiry=lambda response: 30 if response is None else 300,
        )

    def _get_user_data_by_id(self, user_id):
        return self.cache.cache_fetch_fn(
            redis_key=f"api:twitch:helix:user:by-id:{user_id}",
            fetch_fn=lambda: self._fetch_user_data_by_id(user_id),
            expiry=lambda response: 30 if response is None else 300,
        )

    def get_user_id(self, login):
        """Gets the twitch user ID as a string for the given twitch login name,
        utilizing a cache or the twitch API on cache miss.
        If the user is not found, None is returned."""

        user_data = self._get_user_data_by_login(login)
        return user_data["id"] if user_data is not None else None

    def require_user_id(self, login):
        user_id = self.get_user_id(login)
        if user_id is None:
            raise ValueError(f'No user found under login name "{login}" on Twitch')
        return user_id

    def get_login(self, user_id):
        """Gets the twitch login name as a string for the given twitch login name,
        utilizing a cache or the twitch API on cache miss.
        If the user is not found, None is returned."""

        user_data = self._get_user_data_by_id(user_id)
        return user_data["login"] if user_data is not None else None

    def fetch_follow_since(self, from_id, to_id):
        response = self.get("/users/follows", {"from_id": from_id, "to_id": to_id})

        if len(response["data"]) <= 0:
            return None

        return self.parse_datetime(response["data"][0]["followed_at"])

    def get_follow_since(self, from_id, to_id):
        return self.cache.cache_fetch_fn(
            redis_key=f"api:twitch:helix:follow-since:{from_id}:{to_id}",
            serializer=DateTimeSerializer(),
            fetch_fn=lambda: self.fetch_follow_since(from_id, to_id),
            expiry=lambda response: 30 if response is None else 300,
        )

    def get_profile_image_url(self, user_id):
        user_data = self._get_user_data_by_id(user_id)
        return user_data["profile_image_url"] if user_data is not None else None

    def get_user_basics_by_login(self, login):
        user_data = self._get_user_data_by_login(login)
        if user_data is None:
            return None
        return UserBasics(user_data["id"], user_data["login"], user_data["display_name"])

    def _fetch_subscribers_page(self, broadcaster_id, authorization, after_pagination_cursor=None):
        """Fetch a list of subscribers (user IDs) of a broadcaster + a pagination cursor as a tuple."""
        response = self.get(
            "/subscriptions",
            {"broadcaster_id": broadcaster_id, **self._with_pagination(after_pagination_cursor)},
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

        subscribers = [entry["user_id"] for entry in response["data"]]
        pagination_cursor = response["pagination"]["cursor"]

        return subscribers, pagination_cursor

    def fetch_all_subscribers(self, broadcaster_id, authorization):
        """Fetch a list of all subscribers (user IDs) of a broadcaster."""
        return self._fetch_all_pages(self._fetch_subscribers_page, broadcaster_id, authorization)

    def _bulk_fetch_user_data(self, key_type, lookup_keys):
        all_entries = []

        # We can fetch a maximum of 100 users on each helix request
        # so we do it in chunks of 100
        for lookup_keys_chunk in iterate_in_chunks(lookup_keys, 100):
            response = self.get("/users", {key_type: lookup_keys_chunk})

            # using a response map means we don't rely on twitch returning the data entries in the exact
            # order we requested them
            response_map = {response_entry[key_type]: response_entry for response_entry in response["data"]}

            # then fill in the gaps with None
            for lookup_key in lookup_keys_chunk:
                all_entries.append(response_map.get(lookup_key, None))

        return all_entries

    def bulk_get_user_data_by_id(self, user_ids):
        return self.cache.cache_bulk_fetch_fn(
            user_ids,
            redis_key_fn=lambda user_id: f"api:twitch:helix:user:by-id:{user_id}",
            fetch_fn=lambda user_ids: self._bulk_fetch_user_data("id", user_ids),
            expiry=lambda response: 30 if response is None else 300,
        )

    def bulk_get_user_data_by_login(self, logins):
        return self.cache.cache_bulk_fetch_fn(
            logins,
            redis_key_fn=lambda login: f"api:twitch:helix:user:by-login:{login}",
            fetch_fn=lambda logins: self._bulk_fetch_user_data("login", logins),
            expiry=lambda response: 30 if response is None else 300,
        )

    def bulk_get_user_basics_by_id(self, user_ids):
        bulk_user_data = self.bulk_get_user_data_by_id(user_ids)
        return [
            UserBasics(user_data["id"], user_data["login"], user_data["display_name"])
            if user_data is not None
            else None
            for user_data in bulk_user_data
        ]

    def bulk_get_user_basics_by_login(self, logins):
        bulk_user_data = self.bulk_get_user_data_by_login(logins)
        return [
            UserBasics(user_data["id"], user_data["login"], user_data["display_name"])
            if user_data is not None
            else None
            for user_data in bulk_user_data
        ]
