from typing import Optional, ContextManager

import logging

import redis
from redis import Redis
from redis.client import Pipeline

log = logging.getLogger(__name__)


class RedisManager:
    """
    Responsible for making sure exactly one instance of Redis
    is initialized with the right arguments, and returns when the
    get-method is called.
    """

    redis: Optional[Redis] = None

    @staticmethod
    def init(**options) -> None:
        if RedisManager.redis is not None:
            raise ValueError("RedisManager.init has already been called once")

        if "decode_responses" in options:
            raise ValueError("You may not change decode_responses in RedisManager.init options")

        RedisManager.redis = Redis(decode_responses=True, **options)

    @staticmethod
    def get() -> Redis:
        if RedisManager.redis is None:
            raise ValueError("RedisManager.get called before RedisManager.init")

        return RedisManager.redis

    @staticmethod
    def pipeline_context() -> ContextManager[Pipeline]:
        return redis.utils.pipeline(RedisManager.get())

    @classmethod
    def publish(cls, channel: str, message: str) -> int:
        if cls.redis is None:
            raise ValueError("RedisManager.publish called before RedisManager.init")

        return cls.redis.publish(channel, message)
