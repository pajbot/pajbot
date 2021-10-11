from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import logging
from collections import UserDict

from pajbot.managers.redis import RedisManager
from pajbot.streamhelper import StreamHelper

if TYPE_CHECKING:
    from pajbot.managers.redis import RedisType

log = logging.getLogger(__name__)


class KVIData:
    def __init__(self, streamer: str, kvi_id: str) -> None:
        self.key = f"{streamer}:kvi"
        self.id = kvi_id

    def set(self, new_value: int, redis: Optional[RedisType] = None) -> None:
        if redis is None:
            redis = RedisManager.get()

        redis.hset(self.key, self.id, new_value)

    def get(self, redis: Optional[RedisType] = None) -> int:
        if redis is None:
            redis = RedisManager.get()

        value: int = 0

        try:
            raw_value = redis.hget(self.key, self.id)
            if raw_value:
                value = int(raw_value)
        except (TypeError, ValueError):
            value = 0

        return value

    def inc(self) -> None:
        redis = RedisManager.get()
        old_value = self.get(redis=redis)
        self.set(old_value + 1, redis=redis)

    def dec(self) -> None:
        redis = RedisManager.get()
        old_value = self.get(redis=redis)
        self.set(old_value - 1, redis=redis)

    def __str__(self) -> str:
        return str(self.get())


class KVIManager(UserDict):
    def __init__(self) -> None:
        self.streamer = StreamHelper.get_streamer()
        super().__init__(self)

    def __getitem__(self, kvi_id: str) -> KVIData:
        return KVIData(self.streamer, kvi_id)
