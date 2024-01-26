from __future__ import annotations

from typing import Any, Optional, Union

import logging
import math
import time
from datetime import datetime, timezone

from pajbot import utils
from pajbot.apiwrappers.response_cache import (
    ClassInstanceSerializer,
    DateTimeSerializer,
    ListSerializer,
    TwitchChannelEmotesSerializer,
)
from pajbot.apiwrappers.twitch.base import BaseTwitchAPI
from pajbot.models.emote import Emote
from pajbot.models.user import UserBasics, UserChannelInformation, UserStream
from pajbot.utils import iterate_in_chunks

from requests import HTTPError

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

    def jsonify(self) -> dict[str, str]:
        return {
            "id": self.id,
            "name": self.name,
            "box_art_url": self.box_art_url,
        }

    @staticmethod
    def from_json(json_data: dict[str, str]) -> TwitchGame:
        return TwitchGame(
            json_data["id"],
            json_data["name"],
            json_data["box_art_url"],
        )


class TwitchBannedUser:
    def __init__(
        self,
        user_id: str,
        user_login: str,
        user_name: str,
        created_at: str,
        expires_at: str,
        reason: str,
        moderator_id: str,
        moderator_login: str,
        moderator_name: str,
    ):
        self.user_id = user_id
        self.user_login = user_login
        self.user_name = user_name
        self.created_at = created_at
        self.expires_at = expires_at
        self.reason = reason
        self.moderator_id = moderator_id
        self.moderator_login = moderator_login
        self.moderator_name = moderator_name

    def jsonify(self):
        return {
            "user_id": self.user_id,
            "user_login": self.user_login,
            "user_name": self.user_name,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "reason": self.reason,
            "moderator_id": self.moderator_id,
            "moderator_login": self.moderator_login,
            "moderator_name": self.moderator_name,
        }

    @staticmethod
    def from_json(json_data):
        return TwitchBannedUser(
            json_data["user_id"],
            json_data["user_login"],
            json_data["user_name"],
            json_data["created_at"],
            json_data["expires_at"],
            json_data["reason"],
            json_data["moderator_id"],
            json_data["moderator_login"],
            json_data["moderator_name"],
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

    def jsonify(self) -> dict[str, Union[str, int]]:
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
    # TODO(typing): Figure out a better way to express the JSON body as a type as Dict[str, str] is not accurate here
    def from_json(json_data: Any) -> TwitchVideo:
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


class TwitchBadgeVersion:
    def __init__(
        self, id: str, image_url_1x: str, image_url_2x: str, image_url_4x: str, description: str, title: str
    ) -> None:
        self.id = id
        self.image_url_1x = image_url_1x
        self.image_url_2x = image_url_2x
        self.image_url_4x = image_url_4x
        self.description = description
        self.title = title

    def jsonify(self) -> dict[str, str]:
        return {
            "id": self.id,
            "image_url_1x": self.image_url_1x,
            "image_url_2x": self.image_url_2x,
            "image_url_4x": self.image_url_4x,
            "description": self.description,
            "title": self.title,
        }

    @staticmethod
    def from_json(json_data: dict[str, Any]) -> TwitchBadgeVersion:
        return TwitchBadgeVersion(
            json_data["id"],
            json_data["image_url_1x"],
            json_data["image_url_2x"],
            json_data["image_url_4x"],
            json_data["description"],
            json_data["title"],
        )


class TwitchBadgeSet:
    def __init__(self, set_id: str, versions: list[TwitchBadgeVersion]) -> None:
        self.set_id = set_id
        self.versions = versions

    def jsonify(self) -> dict[str, Any]:
        return {
            "set_id": self.set_id,
            "versions": [v.jsonify() for v in self.versions],
        }

    @staticmethod
    def from_json(json_data: dict[str, Any]) -> TwitchBadgeSet:
        return TwitchBadgeSet(
            json_data["set_id"],
            [TwitchBadgeVersion.from_json(v) for v in json_data["versions"]],
        )


TwitchBadgeSets = list[TwitchBadgeSet]


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
            if e.response is None:
                raise e

            if e.response.status_code == 429:
                # retry once after rate limit resets...
                rate_limit_reset = datetime.fromtimestamp(int(e.response.headers["Ratelimit-Reset"]), tz=timezone.utc)
                time_to_wait = rate_limit_reset - utils.now()
                time.sleep(math.ceil(time_to_wait.total_seconds()))
                return super().request(method, endpoint, params, headers, authorization, json)

            raise e

    @staticmethod
    def _with_pagination(after_pagination_cursor: Optional[str] = None) -> dict[str, str]:
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

    # TODO(typing): Figure out a better way to express the Get Users body as a type
    def _fetch_user_data_by_login(self, login: str) -> Optional[dict[str, Any]]:
        response = self.get("/users", {"login": login})

        if len(response["data"]) <= 0:
            return None

        return response["data"][0]

    # TODO(typing): Figure out a better way to express the Get Users body as a type
    def _fetch_user_data_by_id(self, user_id: str) -> Optional[dict[str, Any]]:
        response = self.get("/users", {"id": user_id})

        if len(response["data"]) <= 0:
            return None

        return response["data"][0]

    # TODO(typing): Figure out a better way to express the Get Users body as a type
    def _fetch_user_data_from_authorization(self, authorization) -> dict[str, Any]:
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

    def _fetch_follow_since(self, broadcaster_id: str, user_id: str, authorization) -> Optional[datetime]:
        response = self.get(
            "/channels/followers",
            {
                "broadcaster_id": broadcaster_id,
                "user_id": user_id,
            },
            authorization=authorization,
        )

        if len(response["data"]) <= 0:
            return None

        return self.parse_datetime(response["data"][0]["followed_at"])

    def get_follow_since(self, broadcaster_id: str, user_id: str, authorization) -> Optional[datetime]:
        return self.cache.cache_fetch_fn(
            redis_key=f"api:twitch:helix:follow-since:{broadcaster_id}:{user_id}",
            serializer=DateTimeSerializer(),
            fetch_fn=lambda: self._fetch_follow_since(broadcaster_id, user_id, authorization),
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

    def _fetch_subscribers_page(
        self, broadcaster_id: str, authorization, after_pagination_cursor: Optional[str] = None
    ) -> tuple[list[UserBasics], Optional[str]]:
        """Fetch a list of subscribers (user IDs) of a broadcaster + a pagination cursor as a tuple."""
        response = self.get(
            "/subscriptions",
            {"broadcaster_id": broadcaster_id, "first": 100, **self._with_pagination(after_pagination_cursor)},
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

        subscribers = [
            UserBasics(entry["user_id"], entry["user_login"], entry["user_name"])
            for entry in response["data"]
            # deleted users can appear with empty name https://github.com/twitchdev/issues/issues/717
            if entry["user_login"] is not None and entry["user_login"] != ""
        ]
        pagination_cursor = response["pagination"].get("cursor", None)

        return subscribers, pagination_cursor

    def fetch_all_subscribers(self, broadcaster_id: str, authorization) -> set[UserBasics]:
        """Fetch a list of all subscribers (user IDs) of a broadcaster."""
        subscribers = self._fetch_all_pages(self._fetch_subscribers_page, broadcaster_id, authorization)

        # Dedupe the list of subscribers since the API can return the same IDs multiple times

        return set(subscribers)

    def _bulk_fetch_user_data(self, key_type: str, lookup_keys: list[str]) -> list[Optional[Any]]:
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

    # TODO(typing): Figure out a better way to express the Get Users body as a type
    def bulk_get_user_data_by_id(self, user_ids: list[str]) -> list[Optional[Any]]:
        return self.cache.cache_bulk_fetch_fn(
            user_ids,
            redis_key_fn=lambda user_id: f"api:twitch:helix:user:by-id:{user_id}",
            fetch_fn=lambda user_ids: self._bulk_fetch_user_data("id", user_ids),
            expiry=lambda response: 30 if response is None else 300,
        )

    # TODO(typing): Figure out a better way to express the Get Users body as a type
    def bulk_get_user_data_by_login(self, logins: list[str]) -> list[Optional[Any]]:
        return self.cache.cache_bulk_fetch_fn(
            logins,
            redis_key_fn=lambda login: f"api:twitch:helix:user:by-login:{login}",
            fetch_fn=lambda logins: self._bulk_fetch_user_data("login", logins),
            expiry=lambda response: 30 if response is None else 300,
        )

    def bulk_get_user_basics_by_id(self, user_ids: list[str]) -> list[Optional[UserBasics]]:
        bulk_user_data = self.bulk_get_user_data_by_id(user_ids)
        return [
            (
                UserBasics(user_data["id"], user_data["login"], user_data["display_name"])
                if user_data is not None
                else None
            )
            for user_data in bulk_user_data
        ]

    def bulk_get_user_basics_by_login(self, logins: list[str]) -> list[Optional[UserBasics]]:
        bulk_user_data = self.bulk_get_user_data_by_login(logins)
        return [
            (
                UserBasics(user_data["id"], user_data["login"], user_data["display_name"])
                if user_data is not None
                else None
            )
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

    def _fetch_videos_by_user_id(self, user_id: str) -> list[TwitchVideo]:
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

    def get_videos_by_user_id(self, user_id: str) -> list[TwitchVideo]:
        return self.cache.cache_fetch_fn(
            redis_key=f"api:twitch:helix:videos:by-id:{user_id}",
            fetch_fn=lambda: self._fetch_videos_by_user_id(user_id),
            serializer=ListSerializer(TwitchVideo),
            expiry=lambda response: 30 if response is None else 300,
        )

    def _fetch_games(self, key_type: str, lookup_keys: list[str]) -> list[Optional[TwitchGame]]:
        all_entries: list[Optional[TwitchGame]] = []

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
                    all_entries.append(TwitchGame(game_dict["id"], game_dict["name"], game_dict["box_art_url"]))

        return all_entries

    def get_games_by_id(self, game_ids: list[str]) -> list[TwitchGame]:
        return self.cache.cache_bulk_fetch_fn(
            game_ids,
            redis_key_fn=lambda game_id: f"api:twitch:helix:game:by-id:{game_id}",
            fetch_fn=lambda game_ids: self._fetch_games("id", game_ids),
            serializer=ClassInstanceSerializer(TwitchGame),
            expiry=lambda response: 300 if response is None else 7200,
        )

    def get_games_by_name(self, game_names: list[str]) -> list[TwitchGame]:
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

    def modify_channel_information(self, broadcaster_id: str, body: dict[str, str], authorization=None) -> bool:
        if not body:
            log.error(
                "Invalid call to modify_channel_information, missing query parameter(s). game_id or title must be specified"
            )
            return False

        response = self.patch("/channels", {"broadcaster_id": broadcaster_id}, authorization=authorization, json=body)

        return response.status_code == 204

    def fetch_global_emotes(self) -> list[Emote]:
        # circular import prevention
        from pajbot.managers.emote import EmoteManager

        resp = self.get("/chat/emotes/global")

        return [EmoteManager.twitch_emote(str(emote["id"]), emote["name"]) for emote in resp["data"]]

    def get_global_emotes(self, force_fetch=False) -> list[Emote]:
        return self.cache.cache_fetch_fn(
            redis_key="api:twitch:helix:global-emotes",
            fetch_fn=lambda: self.fetch_global_emotes(),
            serializer=ListSerializer(Emote),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )

    def fetch_channel_emotes(self, channel_id: str, channel_name: str) -> tuple[list[Emote], list[Emote], list[Emote]]:
        """Returns a tuple of three lists of emotes, each one corresponding to tier 1, tier 2 and tier 3 respectively.
        Tier 2 and Tier 3 ONLY contain the respective extra emotes added to that tier."""
        # circular import prevention
        from pajbot.managers.emote import EmoteManager

        resp = self.get("/chat/emotes", {"broadcaster_id": channel_id})

        emotes = resp["data"]
        if len(emotes) <= 0:
            log.warning(f"No subscription emotes found for channel {channel_name}")
            return [], [], []

        ret_data: tuple[list[Emote], list[Emote], list[Emote]] = ([], [], [])
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
    ) -> tuple[list[Emote], list[Emote], list[Emote]]:
        return self.cache.cache_fetch_fn(
            redis_key=f"api:twitch:helix:channel-emotes:{channel_id}",
            fetch_fn=lambda: self.fetch_channel_emotes(channel_id, channel_name),
            serializer=TwitchChannelEmotesSerializer(),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )

    def send_chat_announcement(self, channel_id: str, bot_id: str, message: str, authorization) -> None:
        """Posts the message and colour provided in order to post an announcement.
        channel_id, bot_id and message are all required fields. bot_id must match the user ID
        in authorization.
        Messages longer than 500 characters are truncated by Twitch.
        An exception is raised if there are any invalid or missing details."""
        self.post_204(
            "/chat/announcements",
            {"broadcaster_id": channel_id, "moderator_id": bot_id},
            authorization=authorization,
            json={"message": message},
        )

    def _delete_chat_messages(
        self, channel_id: str, bot_id: str, authorization, message_id: Optional[str] = None
    ) -> None:
        """Deletes message entry from helix using the message_id. If no message_id is provided, the request removes all messages in chat.
        channel_id and bot_id are required fields. bot_id must match the user ID in authorization.
        An exception is raised if there are any invalid or missing details."""
        self.delete(
            "/moderation/chat",
            {"broadcaster_id": channel_id, "moderator_id": bot_id, "message_id": message_id},
            authorization=authorization,
        )

    def delete_single_message(self, channel_id: str, bot_id: str, authorization, message_id: str) -> None:
        """Deletes a single message from the chatroom using the message_id.
        channel_id, bot_id and message_id are all required fields. bot_id must match the user ID
        in authorization.
        An exception is raised if there are any invalid or missing details."""
        self._delete_chat_messages(channel_id, bot_id, authorization, message_id)

    def delete_all_messages(self, channel_id: str, bot_id: str, authorization) -> None:
        """Deletes all messages from the chatroom.
        channel_id and bot_id are required fields. bot_id must match the user ID in authorization.
        An exception is raised if there are any invalid or missing details."""
        self._delete_chat_messages(channel_id, bot_id, authorization)

    def _update_chat_settings(
        self,
        channel_id: str,
        bot_id: str,
        authorization,
        emote_mode: Optional[bool] = None,
        follower_mode: Optional[bool] = None,
        follower_mode_duration: Optional[int] = None,
        non_moderator_chat_delay: Optional[bool] = None,
        non_moderator_chat_delay_duration: Optional[int] = None,
        slow_mode: Optional[bool] = None,
        slow_mode_wait_time: Optional[int] = None,
        subscriber_mode: Optional[bool] = None,
        unique_chat_mode: Optional[bool] = None,
    ) -> None:
        """Calls the update chat settings Helix endpoint using any of the optional settings.
        channel_id and bot_id are required fields. bot_id must match the user ID in authorization.
        An exception is raised if there are any invalid or missing details."""
        self.patch(
            "/chat/settings",
            {"broadcaster_id": channel_id, "moderator_id": bot_id},
            authorization=authorization,
            json={
                "emote_mode": emote_mode,
                "follower_mode": follower_mode,
                "follower_mode_duration": follower_mode_duration,
                "non_moderator_chat_delay": non_moderator_chat_delay,
                "non_moderator_chat_delay_duration": non_moderator_chat_delay_duration,
                "slow_mode": slow_mode,
                "slow_mode_wait_time": slow_mode_wait_time,
                "subscriber_mode": subscriber_mode,
                "unique_chat_mode": unique_chat_mode,
            },
        )

    def update_follower_mode(
        self,
        channel_id: str,
        bot_id: str,
        authorization,
        state: bool,
        duration_m: Optional[int] = None,
    ) -> None:
        """Calls the _update_chat_settings function using the state and duration_m parameters.
        duration_m is in minutes.
        bot_id must match the user ID in authorization."""
        self._update_chat_settings(
            channel_id,
            bot_id,
            authorization,
            follower_mode=state,
            follower_mode_duration=duration_m,
        )

    def update_emote_only_mode(self, channel_id: str, bot_id: str, authorization, emote_mode: bool):
        """Calls the _unique_chat_settings function using the emote_mode parameter.
        channel_id, bot_id and emote_mode are all required fields. bot_id must match the user ID in authorization."""
        self._update_chat_settings(channel_id, bot_id, authorization, emote_mode=emote_mode)

    def update_unique_chat_mode(self, channel_id: str, bot_id: str, authorization, unique_chat_mode: bool) -> None:
        """Calls the _update_chat_settings function using the unique_chat_mode parameter.
        channel_id, bot_id and unique_chat_mode are all required fields. bot_id must match the user ID in authorization.
        """
        self._update_chat_settings(channel_id, bot_id, authorization, unique_chat_mode=unique_chat_mode)

    def update_slow_mode(
        self, channel_id: str, bot_id: str, authorization, slow_mode: bool, slow_mode_wait_time: int
    ) -> None:
        """Calls the _update_chat_settings function using the slow_mode and slow_mode_wait_time parametes.
        channel_id, bot_id, slow_mode and slow_mode_wait_time are all required fields. bot_id must match the user ID in authorization.
        """
        self._update_chat_settings(
            channel_id, bot_id, authorization, slow_mode=slow_mode, slow_mode_wait_time=slow_mode_wait_time
        )

    def update_sub_mode(self, channel_id: str, bot_id: str, authorization, subscriber_mode: bool) -> None:
        """Calls the _update_chat_settings function using the subscriber_mode parameter.
        channel_id, bot_id and subscriber_mode are all required fields. bot_id must match the user ID in authorization.
        """
        self._update_chat_settings(channel_id, bot_id, authorization, subscriber_mode=subscriber_mode)

    def _fetch_moderators_page(
        self,
        broadcaster_id: str,
        authorization,
        after_pagination_cursor=None,
    ):
        """Calls the Get Moderators Helix endpoint using the broadcaster_id parameter.
        broadcaster_id is a required field. broadcaster_id must match the user ID in authorization."""
        response = self.get(
            "/moderation/moderators",
            {"broadcaster_id": broadcaster_id, "first": 100, **self._with_pagination(after_pagination_cursor)},
            authorization=authorization,
        )

        moderators = [
            UserBasics(entry["user_id"], entry["user_login"], entry["user_name"]) for entry in response["data"]
        ]
        pagination_cursor = response["pagination"].get("cursor", None)

        return moderators, pagination_cursor

    def fetch_all_moderators(self, broadcaster_id: str, authorization):
        """Calls the _fetch_moderators_page function using the broadcaster_id parameter.
        broadcaster_id is a required field and must match the user ID in authorization."""
        moderator_ids = self._fetch_all_pages(self._fetch_moderators_page, broadcaster_id, authorization)

        moderator_ids = list(set(moderator_ids))

        return moderator_ids

    def _fetch_vips_page(
        self,
        broadcaster_id: str,
        authorization,
        after_pagination_cursor: Optional[str] = None,
    ) -> tuple[list[UserBasics], Optional[str]]:
        """Calls the Get VIPs Helix endpoint using the broadcaster_id parameter.
        broadcaster_id is a required field and must match the user ID in authorization."""
        response = self.get(
            "/channels/vips",
            {"broadcaster_id": broadcaster_id, "first": 100, **self._with_pagination(after_pagination_cursor)},
            authorization=authorization,
        )

        vips = [UserBasics(entry["user_id"], entry["user_login"], entry["user_name"]) for entry in response["data"]]
        pagination_cursor = response["pagination"].get("cursor", None)

        return vips, pagination_cursor

    def fetch_all_vips(self, broadcaster_id: str, authorization) -> set[UserBasics]:
        """Calls the _fetch_vips_page function using the broadcaster_id parameter.
        broadcaster_id is a required field and must match the user ID in authorization."""
        vips = self._fetch_all_pages(self._fetch_vips_page, broadcaster_id, authorization)

        return set(vips)

    def ban_user(
        self,
        broadcaster_id: str,
        bot_id: str,
        authorization,
        user_id: str,
        reason: Optional[str] = None,
    ) -> tuple[str, Optional[str]]:
        """Calls the Ban User Helix endpoint using the broadcaster_id, bot_id, reason & user_id parameters.
        broadcaster_id, bot_id & user_id are all required parameters. bot_id must match the user_id in authorization.
        """
        response = self.post(
            "/moderation/bans",
            {"broadcaster_id": broadcaster_id, "moderator_id": bot_id},
            authorization=authorization,
            json={"data": {"reason": reason, "user_id": user_id}},
        )

        created_at = response["data"][0]["created_at"]
        end_time = response["data"][0]["end_time"]

        return created_at, end_time

    def timeout_user(
        self,
        broadcaster_id: str,
        bot_id: str,
        authorization,
        user_id: str,
        duration: int,
        reason: Optional[str] = None,
    ) -> tuple[str, Optional[str]]:
        """Calls the Ban User Helix endpoint using the broadcaster_id, bot_id, reason & user_id parameters.
        broadcaster_id, bot_id & user_id are all required parameters. bot_id must match the user_id in authorization.
        duration is in seconds
        """
        response = self.post(
            "/moderation/bans",
            {"broadcaster_id": broadcaster_id, "moderator_id": bot_id},
            authorization=authorization,
            json={"data": {"reason": reason, "user_id": user_id, "duration": duration}},
        )

        created_at = response["data"][0]["created_at"]
        end_time = response["data"][0]["end_time"]

        return created_at, end_time

    def unban_user(
        self,
        broadcaster_id: str,
        bot_id: str,
        user_id: str,
        authorization,
    ) -> None:
        """Calls the Unban User Helix endpoint using the broadcaster_id, bot_user & user_id parameters.
        All parameters are required. bot_id must match the user_id in authorization."""
        self.delete(
            "/moderation/bans",
            {"broadcaster_id": broadcaster_id, "moderator_id": bot_id, "user_id": user_id},
            authorization=authorization,
        )

    def _get_banned_users(
        self,
        broadcaster_id: str,
        authorization,
        user_id: Optional[str] = None,
        after_pagination_cursor: Optional[str] = None,
    ) -> tuple[list[TwitchBannedUser], Optional[str]]:
        """Calls the Get Banned Users Helix endpoint using the broadcaster_id & user_id parameter.
        broadcaster_id is a required field and must match the user ID in authorization."""
        response = self.get(
            "/moderation/banned",
            {
                "broadcaster_id": broadcaster_id,
                "user_id": user_id,
                "first": 100,
                **self._with_pagination(after_pagination_cursor),
            },
            authorization=authorization,
        )

        users = [TwitchBannedUser.from_json(data) for data in response["data"]]
        pagination_cursor = response["pagination"].get("cursor", None)

        return users, pagination_cursor

    def get_banned_user(self, broadcaster_id: str, authorization, user_id: str) -> Optional[TwitchBannedUser]:
        """Calls the _get_banned_users function using the broadcaster_id and user_id parameter.
        All parameters are required and broadcaster_id must match the user ID in authorization."""
        response, _ = self._get_banned_users(broadcaster_id, authorization, user_id)

        return response[0] if len(response) > 0 else None

    def send_whisper(self, sender_id: str, recepient_id: str, message: str, authorization) -> None:
        """Calls the Helix Send Whisper endpoint
        sender_id must match user id in authorization.
        message must be at most 500 characters if sending a whisper to a new user, or 10,000 characters if sending to a user that has whispered you before.
        messages that are too long will be truncated by Twitch.
        """
        self.post_204(
            "/whispers",
            {"from_user_id": sender_id, "to_user_id": recepient_id},
            authorization=authorization,
            json={"message": message},
        )

    def _fetch_chatters_page(
        self,
        broadcaster_id: str,
        moderator_id: str,
        authorization,
        after_pagination_cursor=None,
    ) -> tuple[list[UserBasics], Optional[str]]:
        """
        Calls the Get Chatters Helix endpoint using the broadcaster_id parameter.
        broadcaster_id is a required field. broadcaster_id must be a channel the moderator_id user has moderator privileges in.
        moderator_id is a required field. moderator_id must match the user ID in authorization.
        """

        response = self.get(
            "/chat/chatters",
            {
                "broadcaster_id": broadcaster_id,
                "moderator_id": moderator_id,
                "first": 1000,
                **self._with_pagination(after_pagination_cursor),
            },
            authorization=authorization,
        )

        chatters = [UserBasics(entry["user_id"], entry["user_login"], entry["user_name"]) for entry in response["data"]]
        pagination_cursor = response["pagination"].get("cursor", None)

        return chatters, pagination_cursor

    def get_all_chatters(self, broadcaster_id: str, moderator_id: str, authorization) -> list[UserBasics]:
        """
        Calls the _fetch_chatters_page function using the broadcaster_id & moderator_id parameter.
        broadcaster_id is a required field. broadcaster_id must be a channel the moderator_id user has moderator privileges in.
        moderator_id is a required field. moderator_id must match the user ID in authorization.
        """

        chatters = self._fetch_all_pages(self._fetch_chatters_page, broadcaster_id, moderator_id, authorization)

        chatters = list(set(chatters))

        return chatters

    def get_channel_badges(self, broadcaster_id: str) -> TwitchBadgeSets:
        """
        Calls the Get Channel Chat Badges endpoint https://dev.twitch.tv/docs/api/reference/#get-channel-chat-badges
        broadcaster_id is a required field, it specifies the Twitch User ID of the channel whose chat badges you want to get.
        """

        response = self.get(
            "/chat/badges",
            {
                "broadcaster_id": broadcaster_id,
            },
        )

        return [TwitchBadgeSet.from_json(d) for d in response["data"]]
