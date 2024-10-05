from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import logging
from collections import UserDict

from pajbot.managers.redis import RedisManager
from pajbot.streamhelper import StreamHelper

import regex as re

if TYPE_CHECKING:
    from pajbot.managers.redis import RedisType


KVI_ARGUMENT_REGEX = re.compile(r"^([\w_-]+)(?: ([0-9]+))?$")
KVI_PROHIBITED_KEYS = "active_subs"

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

    def inc(self, amount: int = 1) -> int:
        """
        Increase the value of the given counter by `amount` and return the final result
        """
        redis = RedisManager.get()
        old_value = self.get(redis=redis)
        new_value = old_value + amount
        self.set(new_value, redis=redis)
        return new_value

    def dec(self, amount: int = 1) -> int:
        """
        Decrease the value of the given counter by `amount` and return the final result
        """
        redis = RedisManager.get()
        old_value = self.get(redis=redis)
        new_value = old_value - amount
        self.set(new_value, redis=redis)
        return new_value

    def __str__(self) -> str:
        return str(self.get())


class KVIManager(UserDict):
    def __init__(self) -> None:
        self.streamer = StreamHelper.get_streamer()
        super().__init__(self)

    def __getitem__(self, kvi_id: str) -> KVIData:
        return KVIData(self.streamer, kvi_id)


def parse_kvi_arguments(input_str: str) -> tuple[Optional[str], int]:
    amount = 1

    if not input_str:
        return None, amount

    argument_match = KVI_ARGUMENT_REGEX.match(input_str)

    if not argument_match:
        return None, amount

    kvi_key = argument_match.group(1)

    if not kvi_key:
        return None, amount

    kvi_amount = argument_match.group(2)
    if kvi_amount:
        try:
            amount = int(kvi_amount)
        except ValueError:
            pass

    return kvi_key, amount
