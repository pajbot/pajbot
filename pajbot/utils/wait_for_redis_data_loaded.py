import time

import logging
from redis import BusyLoadingError

log = logging.getLogger(__name__)


def wait_for_redis_data_loaded(redis):
    while True:
        try:
            redis.ping()
        except BusyLoadingError:
            log.warning("Redis not done loading, will retry in 2 seconds...")
            time.sleep(2)
            continue
        break
