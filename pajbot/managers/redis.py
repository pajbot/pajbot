from __future__ import annotations

from typing import Any, ContextManager, Optional

import logging

import redis
import redis.asyncio
from redis import Redis
from redis.client import Pipeline

type _StrType = str
type RedisType = Redis[_StrType]

log = logging.getLogger(__name__)

type AsyncRedisType = redis.asyncio.Redis[str]


class RedisManager:
    """
    Responsible for making sure exactly one instance of Redis
    is initialized with the right arguments, and returns when the
    get-method is called.
    """

    redis: Optional[RedisType] = None
    redis_async: Optional[AsyncRedisType] = None

    @staticmethod
    def init(options: dict[Any, Any]) -> None:
        if RedisManager.redis is not None:
            raise ValueError("RedisManager.init has already been called once")

        if "decode_responses" in options:
            raise ValueError("You may not change decode_responses in RedisManager.init options")

        options["decode_responses"] = True

        RedisManager.redis = Redis(**options)

        RedisManager.redis_async = redis.asyncio.Redis(**options)

    @staticmethod
    def get() -> RedisType:
        if RedisManager.redis is None:
            raise ValueError("RedisManager.get called before RedisManager.init")

        return RedisManager.redis

    @staticmethod
    def get_async() -> AsyncRedisType:
        if RedisManager.redis_async is None:
            raise ValueError("RedisManager.get_async called before RedisManager.init")

        return RedisManager.redis_async

    @staticmethod
    def pipeline_context() -> ContextManager[Pipeline[_StrType]]:
        return redis.utils.pipeline(RedisManager.get())

    @classmethod
    def publish(cls, channel: str, message: str) -> int:
        if cls.redis is None:
            raise ValueError("RedisManager.publish called before RedisManager.init")

        return cls.redis.publish(channel, message)
