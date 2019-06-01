import logging
from collections import UserDict

from pajbot.managers.redis import RedisManager
from pajbot.streamhelper import StreamHelper

log = logging.getLogger(__name__)


class KVIData:
    def __init__(self, streamer, kvi_id):
        self.key = "{streamer}:kvi".format(streamer=streamer)
        self.id = kvi_id

    def set(self, new_value, redis=None):
        if redis is None:
            redis = RedisManager.get()

        redis.hset(self.key, self.id, new_value)

    def get(self, redis=None):
        if redis is None:
            redis = RedisManager.get()

        try:
            raw_value = redis.hget(self.key, self.id)
            value = int(raw_value)
        except (TypeError, ValueError):
            value = 0

        return value

    def inc(self):
        redis = RedisManager.get()
        old_value = self.get(redis=redis)
        self.set(old_value + 1, redis=redis)

    def dec(self):
        redis = RedisManager.get()
        old_value = self.get(redis=redis)
        self.set(old_value - 1, redis=redis)

    def __str__(self):
        return str(self.get())


class KVIManager(UserDict):
    def __init__(self):
        self.streamer = StreamHelper.get_streamer()
        UserDict.__init__(self)

    def __getitem__(self, kvi_id):
        return KVIData(self.streamer, kvi_id)
