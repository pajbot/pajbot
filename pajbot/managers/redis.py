from __future__ import annotations

from typing import TYPE_CHECKING, Any, ContextManager, Dict, Optional

import logging

import redis
from redis import Redis
from redis.client import Pipeline

if TYPE_CHECKING:
    _StrType = str
    RedisType = Redis[_StrType]

log = logging.getLogger(__name__)


class RedisManager:
    """
    Responsible for making sure exactly one instance of Redis
    is initialized with the right arguments, and returns when the
    get-method is called.
    """

    redis: Optional[RedisType] = None

    @staticmethod
    def init(options: Dict[Any, Any]) -> None:
        if RedisManager.redis is not None:
            raise ValueError("RedisManager.init has already been called once")

        if "decode_responses" in options:
            raise ValueError("You may not change decode_responses in RedisManager.init options")

        options["decode_responses"] = True

        RedisManager.redis = Redis(**options)

    @staticmethod
    def get() -> RedisType:
        if RedisManager.redis is None:
            raise ValueError("RedisManager.get called before RedisManager.init")

        return RedisManager.redis

    @staticmethod
    def pipeline_context() -> ContextManager[Pipeline[_StrType]]:
        return redis.utils.pipeline(RedisManager.get())

    @classmethod
    def publish(cls, channel: str, message: str) -> int:
        if cls.redis is None:
            raise ValueError("RedisManager.publish called before RedisManager.init")

        return cls.redis.publish(channel, message)
