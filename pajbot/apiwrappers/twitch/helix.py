from typing import Dict, Optional, List, Tuple

import logging
import time

from datetime import datetime, timezone

import math
from requests import HTTPError

from pajbot import utils
from pajbot.apiwrappers.response_cache import (
    DateTimeSerializer,
    ClassInstanceSerializer,
    ListSerializer,
    TwitchChannelEmotesSerializer,
)
from pajbot.apiwrappers.twitch.base import BaseTwitchAPI
from pajbot.models.emote import Emote
from pajbot.models.user import UserBasics, UserChannelInformation, UserStream
from pajbot.utils import iterate_in_chunks

log = logging.getLogger(__name__)


class TwitchGame:
    def __init__(
        self,
        id: str,
        name: str,
        box_art_url: str,
    ):
        self.id: str = id
        self.name: str = name
        self.box_art_url: str = box_art_url

    def jsonify(self):
        return {
            "id": self.id,
            "name": self.name,
            "box_art_url": self.box_art_url,
        }

    @staticmethod
    def from_json(json_data):
        return TwitchGame(
            json_data["id"],
            json_data["name"],
            json_data["box_art_url"],
        )


class TwitchVideo:
    def __init__(
        self,
        id: str,
        user_id: str,
        user_name: str,
        title: str,
        description: str,
        created_at: str,
        published_at: str,
        url: str,
        thumbnail_url: str,
        viewable: str,
        view_count: int,
        language: str,
        video_type: str,
        duration: str,
    ):
        self.id: str = id
        self.user_id: str = user_id
        self.user_name: str = user_name
        self.title: str = title
        self.description: str = description
        self.created_at: str = created_at
        self.published_at: str = published_at
        self.url: str = url
        self.thumbnail_url: str = thumbnail_url
        self.viewable: str = viewable
        self.view_count: int = view_count
        self.language: str = language
        self.video_type: str = video_type
        self.duration: str = duration

    def jsonify(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "title": self.title,
            "description": self.description,
            "created_at": self.created_at,
            "published_at": self.published_at,
            "url": self.url,
            "thumbnail_url": self.thumbnail_url,
            "viewable": self.viewable,
            "view_count": self.view_count,
            "language": self.language,
            "video_type": self.video_type,
            "duration": self.duration,
        }

    @staticmethod
    def from_json(json_data):
        return TwitchVideo(
            json_data["id"],
            json_data["user_id"],
            json_data["user_name"],
            json_data["title"],
            json_data["description"],
            json_data["created_at"],
            json_data["published_at"],
            json_data["url"],
            json_data["thumbnail_url"],
            json_data["viewable"],
            json_data["view_count"],
            json_data["language"],
            json_data["video_type"],
            json_data["duration"],
        )


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

            raise e

    @staticmethod
    def _with_pagination(after_pagination_cursor=None):
        """Returns a dict with extra query parameters based on the given pagination cursor.
        This makes a dict with the ?after=xxxx query parameter if a pagination cursor is present,
        and if no pagination cursor is present, returns an empty dict."""
        if after_pagination_cursor is None:
            return {}  # no extra query parameters

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
            if len(response) <= 0 or pagination_cursor is None:
                break

        return responses

    def _fetch_user_data_by_login(self, login: str):
        response = self.get("/users", {"login": login})

        if len(response["data"]) <= 0:
            return None

        return response["data"][0]

    def _fetch_user_data_by_id(self, user_id):
        response = self.get("/users", {"id": user_id})

        if len(response["data"]) <= 0:
            return None

        return response["data"][0]

    def _fetch_user_data_from_authorization(self, authorization):
        response = self.get("/users", authorization=authorization)

        if len(response["data"]) <= 0:
            raise ValueError("No user returned for given authorization")

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

    def get_user_id(self, login: str) -> Optional[str]:
        """Gets the twitch user ID as a string for the given twitch login name,
        utilizing a cache or the twitch API on cache miss.
        If the user is not found, None is returned."""

        user_data = self._get_user_data_by_login(login)
        return user_data["id"] if user_data is not None else None

    def require_user_id(self, login: str) -> str:
        user_id = self.get_user_id(login)
        if user_id is None:
            raise ValueError(f'No user found under login name "{login}" on Twitch')
        return user_id

    def get_login(self, user_id: str) -> Optional[str]:
        """Gets the twitch login name as a string for the given twitch login name,
        utilizing a cache or the twitch API on cache miss.
        If the user is not found, None is returned."""

        user_data = self._get_user_data_by_id(user_id)
        return user_data["login"] if user_data is not None else None

    def fetch_channel_information(self, user_id: str) -> Optional[UserChannelInformation]:
        response = self.get("/channels", {"broadcaster_id": user_id})

        if len(response["data"]) <= 0:
            return None

        info = response["data"][0]

        return UserChannelInformation(info["broadcaster_language"], info["game_id"], info["game_name"], info["title"])

    def get_channel_information(self, user_id: str) -> Optional[UserChannelInformation]:
        """Gets the channel information of a Twitch user for the given Twitch user ID,
        utilizing a cache or the Twitch API on cache miss.
        If no channel with the user exists, None is returned.
        https://dev.twitch.tv/docs/api/reference#get-channel-information"""
        return self.cache.cache_fetch_fn(
            redis_key=f"api:twitch:helix:channel-information:{user_id}",
            serializer=ClassInstanceSerializer(UserChannelInformation),
            fetch_fn=lambda: self.fetch_channel_information(user_id),
            expiry=lambda response: 30 if response else 300,
        )

    def fetch_follow_since(self, from_id, to_id):
        response = self.get("/users/follows", {"from_id": from_id, "to_id": to_id})

        if len(response["data"]) <= 0:
            return None

        return self.parse_datetime(response["data"][0]["followed_at"])

    def get_follow_since(self, from_id: str, to_id: str):
        return self.cache.cache_fetch_fn(
            redis_key=f"api:twitch:helix:follow-since:{from_id}:{to_id}",
            serializer=DateTimeSerializer(),
            fetch_fn=lambda: self.fetch_follow_since(from_id, to_id),
            expiry=lambda response: 30 if response is None else 300,
        )

    def get_profile_image_url(self, user_id: str) -> Optional[str]:
        user_data = self._get_user_data_by_id(user_id)
        return user_data["profile_image_url"] if user_data is not None else None

    def get_user_basics_by_login(self, login: str) -> Optional[UserBasics]:
        user_data = self._get_user_data_by_login(login)
        if user_data is None:
            return None
        return UserBasics(user_data["id"], user_data["login"], user_data["display_name"])

    def require_user_basics_by_login(self, login: str) -> UserBasics:
        user_basics = self.get_user_basics_by_login(login)
        if user_basics is None:
            raise ValueError(f'No user found under login name "{login}" on Twitch')
        return user_basics

    def get_user_basics_by_id(self, user_id: str) -> Optional[UserBasics]:
        user_data = self._get_user_data_by_id(user_id)
        if user_data is None:
            return None
        return UserBasics(user_data["id"], user_data["login"], user_data["display_name"])

    def require_user_basics_by_id(self, user_id: str) -> UserBasics:
        user_basics = self.get_user_basics_by_id(user_id)
        if user_basics is None:
            raise ValueError(f'No user found under user ID "{user_id}" on Twitch')
        return user_basics

    def fetch_user_basics_from_authorization(self, authorization) -> UserBasics:
        """Fetch the UserBasics for the user identified by the given authorization object.
        `authorization` can be a UserAccessTokenManager or a tuple (ClientCredentials, UserAccessToken)."""
        user_data = self._fetch_user_data_from_authorization(authorization)
        return UserBasics(user_data["id"], user_data["login"], user_data["display_name"])

    def _fetch_subscribers_page(self, broadcaster_id, authorization, after_pagination_cursor=None):
        """Fetch a list of subscribers (user IDs) of a broadcaster + a pagination cursor as a tuple."""
        response = self.get(
            "/subscriptions",
            {"broadcaster_id": broadcaster_id, **self._with_pagination(after_pagination_cursor)},
            authorization=authorization,
        )

        # Response with data
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
        #
        # Response at end
        # response =
        # {
        #   "data": [],
        #   "pagination": {},
        # }

        subscribers = [entry["user_id"] for entry in response["data"]]
        pagination_cursor = response["pagination"].get("cursor", None)

        return subscribers, pagination_cursor

    def fetch_all_subscribers(self, broadcaster_id, authorization):
        """Fetch a list of all subscribers (user IDs) of a broadcaster."""
        subscriber_ids = self._fetch_all_pages(self._fetch_subscribers_page, broadcaster_id, authorization)

        # Dedupe the list of subscribers since the API can return the same IDs multiple times
        subscriber_ids = list(set(subscriber_ids))

        return subscriber_ids

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

    def bulk_get_user_basics_by_id(self, user_ids: List[str]) -> List[Optional[UserBasics]]:
        bulk_user_data = self.bulk_get_user_data_by_id(user_ids)
        return [
            UserBasics(user_data["id"], user_data["login"], user_data["display_name"])
            if user_data is not None
            else None
            for user_data in bulk_user_data
        ]

    def bulk_get_user_basics_by_login(self, logins: List[str]) -> List[Optional[UserBasics]]:
        bulk_user_data = self.bulk_get_user_data_by_login(logins)
        return [
            UserBasics(user_data["id"], user_data["login"], user_data["display_name"])
            if user_data is not None
            else None
            for user_data in bulk_user_data
        ]

    def create_clip(self, broadcaster_id: str, authorization, has_delay=False) -> str:
        response = self.post(
            "/clips", {"broadcaster_id": broadcaster_id, "has_delay": has_delay}, authorization=authorization
        )
        clip_id = response["data"][0]["id"]

        return clip_id

    def _fetch_stream_by_user_id(self, user_id: str) -> Optional[UserStream]:
        response = self.get("/streams", {"user_id": user_id})

        if len(response["data"]) <= 0:
            # Stream is offline
            return None

        stream = response["data"][0]

        return UserStream(
            stream["viewer_count"],
            stream["game_id"],
            stream["title"],
            stream["started_at"],
            stream["id"],
        )

    def get_stream_by_user_id(self, user_id: str) -> Optional[UserStream]:
        return self.cache.cache_fetch_fn(
            redis_key=f"api:twitch:helix:stream:by-id:{user_id}",
            fetch_fn=lambda: self._fetch_stream_by_user_id(user_id),
            serializer=ClassInstanceSerializer(UserStream),
            expiry=lambda response: 30 if response is None else 300,
        )

    def _fetch_videos_by_user_id(self, user_id: str) -> List[TwitchVideo]:
        response = self.get("/videos", {"user_id": user_id})

        videos = []

        for video in response["data"]:
            videos.append(
                TwitchVideo(
                    video["id"],
                    video["user_id"],
                    video["user_name"],
                    video["title"],
                    video["description"],
                    video["created_at"],
                    video["published_at"],
                    video["url"],
                    video["thumbnail_url"],
                    video["viewable"],
                    video["view_count"],
                    video["language"],
                    video["type"],
                    video["duration"],
                )
            )

        return videos

    def get_videos_by_user_id(self, user_id: str) -> List[TwitchVideo]:
        return self.cache.cache_fetch_fn(
            redis_key=f"api:twitch:helix:videos:by-id:{user_id}",
            fetch_fn=lambda: self._fetch_videos_by_user_id(user_id),
            serializer=ListSerializer(TwitchVideo),
            expiry=lambda response: 30 if response is None else 300,
        )

    def _fetch_games(self, key_type: str, lookup_keys: List[str]) -> List[Optional[TwitchGame]]:
        all_entries: List[Optional[TwitchGame]] = []

        # We can fetch a maximum of 100 users on each helix request
        # so we do it in chunks of 100
        for lookup_keys_chunk in iterate_in_chunks(lookup_keys, 100):
            response = self.get("/games", {key_type: lookup_keys_chunk})

            # using a response map means we don't rely on twitch returning the data entries in the exact
            # order we requested them
            response_map = {response_entry[key_type]: response_entry for response_entry in response["data"]}

            # then fill in the gaps with None
            for lookup_key in lookup_keys_chunk:
                game_dict = response_map.get(lookup_key, None)
                if game_dict is None:
                    all_entries.append(None)
                else:
                    value: TwitchGame = TwitchGame(**response_map.get(lookup_key, None))
                    all_entries.append(value)

        return all_entries

    def get_games_by_id(self, game_ids: List[str]) -> List[TwitchGame]:
        return self.cache.cache_bulk_fetch_fn(
            game_ids,
            redis_key_fn=lambda game_id: f"api:twitch:helix:game:by-id:{game_id}",
            fetch_fn=lambda game_ids: self._fetch_games("id", game_ids),
            serializer=ClassInstanceSerializer(TwitchGame),
            expiry=lambda response: 300 if response is None else 7200,
        )

    def get_games_by_name(self, game_names: List[str]) -> List[TwitchGame]:
        return self.cache.cache_bulk_fetch_fn(
            game_names,
            redis_key_fn=lambda game_name: f"api:twitch:helix:game:by-name:{game_name}",
            fetch_fn=lambda game_names: self._fetch_games("name", game_names),
            serializer=ClassInstanceSerializer(TwitchGame),
            expiry=lambda response: 300 if response is None else 7200,
        )

    def get_game_by_game_id(self, game_id: str) -> Optional[TwitchGame]:
        games = self.get_games_by_id([game_id])
        if len(games) == 0:
            return None

        return games[0]

    def get_game_by_game_name(self, game_name: str) -> Optional[TwitchGame]:
        games = self.get_games_by_name([game_name])
        if len(games) == 0:
            return None

        return games[0]

    def modify_channel_information(self, broadcaster_id: str, body: Dict[str, str], authorization=None) -> bool:
        if not body:
            log.error(
                "Invalid call to modify_channel_information, missing query parameter(s). game_id or title must be specified"
            )
            return False

        response = self.patch("/channels", {"broadcaster_id": broadcaster_id}, authorization=authorization, json=body)

        return response.status_code == 204

    def fetch_global_emotes(self) -> List[Emote]:
        # circular import prevention
        from pajbot.managers.emote import EmoteManager

        resp = self.get("/chat/emotes/global")

        return [EmoteManager.twitch_emote(str(emote["id"]), emote["name"]) for emote in resp["data"]]

    def get_global_emotes(self, force_fetch=False) -> List[Emote]:
        return self.cache.cache_fetch_fn(
            redis_key="api:twitch:helix:global-emotes",
            fetch_fn=lambda: self.fetch_global_emotes(),
            serializer=ListSerializer(Emote),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )

    def fetch_channel_emotes(self, channel_id: str, channel_name: str) -> Tuple[List[Emote], List[Emote], List[Emote]]:
        """Returns a tuple of three lists of emotes, each one corresponding to tier 1, tier 2 and tier 3 respectively.
        Tier 2 and Tier 3 ONLY contain the respective extra emotes added to that tier."""
        # circular import prevention
        from pajbot.managers.emote import EmoteManager

        resp = self.get("/chat/emotes", {"broadcaster_id": channel_id})

        emotes = resp["data"]
        if len(emotes) <= 0:
            log.warning(f"No subscription emotes found for channel {channel_name}")
            return [], [], []

        ret_data: Tuple[List[Emote], List[Emote], List[Emote]] = ([], [], [])
        for emote in emotes:
            if emote["emote_type"] == "subscriptions":
                tier = 0
                if emote["tier"] == "1000":  # tier 1 emotes
                    tier = 1
                elif emote["tier"] == "2000":  # tier 2 emotes
                    tier = 2
                elif emote["tier"] == "3000":  # tier 3 emotes
                    tier = 3
                else:
                    log.warning(f"Unknown channel emote tier fetched: '{emote}'")
                    continue

                ret_data[tier - 1].append(EmoteManager.twitch_emote(str(emote["id"]), emote["name"]))
            elif emote["emote_type"] == "bitstier":
                # TODO: Figure out where bit emotes fit into pajbot
                pass
            else:
                log.warning(f"Unknown channel emote type fetched: '{emote}'")
        return ret_data

    def get_channel_emotes(
        self, channel_id: str, channel_name: str, force_fetch=False
    ) -> Tuple[List[Emote], List[Emote], List[Emote]]:
        return self.cache.cache_fetch_fn(
            redis_key=f"api:twitch:helix:channel-emotes:{channel_id}",
            fetch_fn=lambda: self.fetch_channel_emotes(channel_id, channel_name),
            serializer=TwitchChannelEmotesSerializer(),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )
