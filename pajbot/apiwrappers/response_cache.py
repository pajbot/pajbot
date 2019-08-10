import json

from abc import ABC, abstractmethod

import logging

from pajbot import utils
from pajbot.models.emote import Emote

log = logging.getLogger(__name__)


class BaseJsonSerializer(ABC):
    def serialize(self, fetch_result):
        if fetch_result is not None:
            fetch_result = self.safe_serialize(fetch_result)

        return json.dumps(fetch_result)

    @abstractmethod
    def safe_serialize(self, fetch_result):
        pass

    def deserialize(self, cache_result):
        cache_result = json.loads(cache_result)
        if cache_result is not None:
            cache_result = self.safe_deserialize(cache_result)
        return cache_result

    @abstractmethod
    def safe_deserialize(self, cache_result):
        pass


class JsonSerializer(BaseJsonSerializer):
    def safe_serialize(self, fetch_result):
        return fetch_result

    def safe_deserialize(self, cache_result):
        return cache_result


class DateTimeSerializer(BaseJsonSerializer):
    # 'null' <=> None
    # '123456' <=> datetime.datetime (milliseconds since UTC epoch)
    def safe_serialize(self, fetch_result):
        return fetch_result.timestamp() * 1000

    def safe_deserialize(self, cache_result):
        return utils.datetime_from_utc_milliseconds(cache_result)


class ClassInstanceSerializer(BaseJsonSerializer):
    """(de)serializes instances using the .jsonify() and .from_json() methods"""

    def __init__(self, cls):
        self.cls = cls

    def safe_serialize(self, fetch_result):
        return fetch_result.jsonify()

    def safe_deserialize(self, cache_result):
        return self.cls.from_json(cache_result)


class ListSerializer(BaseJsonSerializer):
    def __init__(self, cls):
        self.cls = cls

    def safe_serialize(self, fetch_result):
        return [e.jsonify() for e in fetch_result]

    def safe_deserialize(self, cache_result):
        return [self.cls.from_json(c) for c in cache_result]


class TwitchChannelEmotesSerializer(BaseJsonSerializer):
    def safe_serialize(self, fetch_result):
        # fetch_result is a tuple but we don't have to convert it to list manually
        # since the tuple can be iterated just like a list
        return [[e.jsonify() for e in s] for s in fetch_result]

    def safe_deserialize(self, cache_result):
        return tuple([[Emote.from_json(e) for e in s] for s in cache_result])


class APIResponseCache:
    def __init__(self, redis):
        self.redis = redis

    def cache_fetch_fn(self, redis_key, fetch_fn, serializer=JsonSerializer(), expiry=120, force_fetch=False):
        if not force_fetch:
            cache_result = self.redis.get(redis_key)
            if cache_result is not None:
                return serializer.deserialize(cache_result)

        log.debug("Cache Miss: %s", redis_key)
        fetch_result = fetch_fn()

        if callable(expiry):
            # then expiry is a lambda that computes the expiry based upon the fetch result
            expiry = expiry(fetch_result)

        # expiry = 0 can be used to indicate the result should not be cached
        # (Redis will raise an error if we try to SETEX with time = 0 so this check is done before calling Redis)
        if expiry > 0:
            self.redis.setex(redis_key, expiry, serializer.serialize(fetch_result))
        return fetch_result
