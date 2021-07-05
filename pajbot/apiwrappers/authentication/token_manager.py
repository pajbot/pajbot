import json

from abc import abstractmethod, ABC

import logging

from pajbot.apiwrappers.authentication.access_token import AppAccessToken, UserAccessToken

log = logging.getLogger(__name__)


class RedisTokenStorage:
    def __init__(self, redis, cls, redis_key, expire):
        self.redis = redis
        self.cls = cls
        self.redis_key = redis_key
        self.expire = expire

    def load(self):
        cache_result = self.redis.get(self.redis_key)
        if cache_result is None:
            return None

        return self.cls.from_json(json.loads(cache_result))

    def save(self, token):
        if self.expire:
            redis_expire_in = token.expires_in.total_seconds() * token.SHOULD_REFRESH_THRESHOLD
            self.redis.setex(self.redis_key, int(redis_expire_in), json.dumps(token.jsonify()))
        else:
            self.redis.set(self.redis_key, json.dumps(token.jsonify()))


class NoTokenError(Exception):
    pass


class AccessTokenManager(ABC):
    """Manages the lifecycle of OAuth2 tokens"""

    def __init__(self, api, storage, token=None):
        self.api = api
        self.storage = storage
        self._token = token

    def refresh(self):
        """called when the current token should be refreshed"""
        log.debug("Refreshing OAuth token")
        new_token = self._token.refresh(self.api)
        self.storage.save(new_token)
        self._token = new_token

    @abstractmethod
    def fetch_new(self):
        """Attempts to create a new token if possible. Raises a NoTokenError if creating
        a new token is not possible."""
        pass

    def initialize(self):
        """called initially when no token is present, fetches from storage or a new token if possible."""
        storage_result = self.storage.load()

        if storage_result is not None:
            log.debug("Successfully loaded OAuth token from storage")
            self._token = storage_result
        else:
            self._token = self.fetch_new()
            self.storage.save(self._token)

    @property
    def token(self):
        """Get a valid token, attempts to load from storage/request a new token on the first call,
        and refreshes the token as necessary on every invocation."""
        if self._token is None:
            self.initialize()

        if self._token.should_refresh():
            self.refresh()

        return self._token


class AppAccessTokenManager(AccessTokenManager):
    def __init__(self, api, redis, scope=[], token=None):
        redis_key = f"authentication:app-access-token:{api.client_credentials.client_id}:{json.dumps(scope)}"
        storage = RedisTokenStorage(redis, AppAccessToken, redis_key, expire=True)

        super().__init__(api, storage, token)
        self.scope = scope

    def fetch_new(self):
        log.debug("No app access token present, trying to fetch new OAuth token")
        return self.api.get_app_access_token(self.scope)


class UserAccessTokenManager(AccessTokenManager):
    def __init__(self, api, redis, username, user_id, token=None):
        redis_key = f"authentication:user-access-token:{user_id}"
        storage = RedisTokenStorage(redis, UserAccessToken, redis_key, expire=False)

        super().__init__(api, storage, token)
        self.username = username
        self.user_id = user_id

    def fetch_new(self):
        raise NoTokenError(f"No authentication token found for user {self.username} ({self.user_id}) in redis")
