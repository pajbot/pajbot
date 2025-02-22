from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Type, TypeVar

from pajbot.apiwrappers.authentication.access_token import AccessToken, AppAccessToken, IdentityAPI, UserAccessToken
from pajbot.managers.redis import RedisType

log = logging.getLogger(__name__)

_T = TypeVar("_T", bound="AccessToken")


class RedisTokenStorage:
    def __init__(self, redis: RedisType, cls: Type[_T], redis_key: str, expire: bool) -> None:
        self.redis = redis
        self.cls = cls
        self.redis_key = redis_key
        self.expire = expire

    def load(self) -> AccessToken | None:
        cache_result = self.redis.get(self.redis_key)
        if cache_result is None:
            return None

        return self.cls.from_json(json.loads(cache_result))

    def save(self, token: AccessToken) -> None:
        if self.expire and token.expires_in is not None:
            redis_expire_in = token.expires_in.total_seconds() * token.SHOULD_REFRESH_THRESHOLD
            self.redis.setex(self.redis_key, int(redis_expire_in), json.dumps(token.jsonify()))
        else:
            self.redis.set(self.redis_key, json.dumps(token.jsonify()))


class NoTokenError(Exception):
    pass


class AccessTokenManager(ABC):
    """Manages the lifecycle of OAuth2 tokens"""

    def __init__(
        self,
        api: IdentityAPI,
        storage: RedisTokenStorage,
        token: AccessToken | None = None,
    ) -> None:
        self.api = api
        self.storage = storage
        self._token = token

    async def refresh(self) -> None:
        """called when the current token should be refreshed"""
        log.debug("Refreshing OAuth token")
        assert self._token is not None
        new_token = await self._token.refresh(self.api)
        self.storage.save(new_token)
        self._token = new_token

    @abstractmethod
    async def fetch_new(self) -> AccessToken:
        """Attempts to create a new token if possible. Raises a NoTokenError if creating
        a new token is not possible."""
        pass

    async def initialize(self) -> None:
        """called initially when no token is present, fetches from storage or a new token if possible."""
        storage_result = self.storage.load()

        if storage_result is not None:
            log.debug("Successfully loaded OAuth token from storage")
            self._token = storage_result
        else:
            self._token = await self.fetch_new()
            self.storage.save(self._token)

    def invalidate_token(self) -> None:
        """invalidate_token gives consumes the ability to say that this token
        has been invalidated externally, and that any further uses
        of the token must attempt to fetch it from the token storage"""
        self._token = None

    @property
    async def token(self) -> AccessToken:
        """Get a valid token, attempts to load from storage/request a new token on the first call,
        and refreshes the token as necessary on every invocation."""
        if self._token is None:
            await self.initialize()

        assert self._token is not None

        if self._token.should_refresh():
            await self.refresh()

        return self._token


class AppAccessTokenManager(AccessTokenManager):
    def __init__(
        self,
        api: IdentityAPI,
        redis: RedisType,
        scope: list[str] = [],
        token: AppAccessToken | None = None,
    ) -> None:
        redis_key = f"authentication:app-access-token:{api.get_client_credentials().client_id}:{json.dumps(scope)}"
        storage = RedisTokenStorage(redis, AppAccessToken, redis_key, expire=True)

        super().__init__(api, storage, token)
        self.scope = scope

    async def fetch_new(self) -> AppAccessToken:
        log.debug("No app access token present, trying to fetch new OAuth token")
        return await self.api.get_app_access_token(self.scope)


class UserAccessTokenManager(AccessTokenManager):
    def __init__(
        self,
        api: IdentityAPI,
        redis: RedisType,
        username: str,
        user_id: str,
        token: UserAccessToken | None = None,
    ) -> None:
        redis_key = f"authentication:user-access-token:{user_id}"
        storage = RedisTokenStorage(redis, UserAccessToken, redis_key, expire=False)

        super().__init__(api, storage, token)
        self.username = username
        self.user_id = user_id

    async def fetch_new(self) -> UserAccessToken:
        raise NoTokenError(f"No authentication token found for user {self.username} ({self.user_id}) in redis")
