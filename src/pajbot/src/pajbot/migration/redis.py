from __future__ import annotations

from typing import Any, Iterator, Optional

from contextlib import contextmanager

from redis import Redis


class RedisMigratable:
    def __init__(self, redis_options: dict[Any, Any], namespace: str) -> None:
        self.redis_options = redis_options
        self.namespace = namespace

    @contextmanager
    def create_resource(self) -> Iterator[Redis]:
        redis = None

        try:
            redis = Redis(**self.redis_options)
            yield redis
        finally:
            if redis is not None:
                redis.connection_pool.disconnect()

    def get_current_revision(self, redis: Redis) -> Optional[int]:
        response = redis.get(self.namespace + ":schema-version")

        if response is None:
            return None
        else:
            return int(response)

    def set_revision(self, redis: Redis, id: int) -> None:
        redis.set(self.namespace + ":schema-version", id)

    @staticmethod
    def describe_resource() -> str:
        return "redis"
