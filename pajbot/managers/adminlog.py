import datetime
import json

from pajbot.managers import RedisManager
from pajbot.streamhelper import StreamHelper

class AdminLogManager:
    KEY = None

    def get_key():
        if AdminLogManager.KEY is None:
            streamer = StreamHelper.get_streamer()
            AdminLogManager.KEY = '{streamer}:logs:admin'.format(streamer=streamer)
        return AdminLogManager.KEY

    def add_entry(type, source, message, data={}):
        redis = RedisManager.get()

        payload = {
                'type': type,
                'user_id': source.id,
                'message': message,
                'created_at': str(datetime.datetime.now()),
                'data': data,
                }

        redis.lpush(AdminLogManager.get_key(), json.dumps(payload))

    def get_entries(offset=0, limit=50):
        redis = RedisManager.get()

        return [json.loads(entry) for entry in redis.lrange(AdminLogManager.get_key(), offset, limit)]
