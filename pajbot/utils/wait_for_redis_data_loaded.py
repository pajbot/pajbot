from __future__ import annotations

from typing import TYPE_CHECKING

import time

import logging
from redis import BusyLoadingError

if TYPE_CHECKING:
    from pajbot.managers.redis import RedisType

log = logging.getLogger(__name__)


def wait_for_redis_data_loaded(redis: RedisType) -> None:
    while True:
        try:
            redis.ping()
        except BusyLoadingError:
            log.warning("Redis not done loading, will retry in 2 seconds...")
            time.sleep(2)
            continue
        break
