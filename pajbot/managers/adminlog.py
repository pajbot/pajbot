import datetime
import json
import logging

from pajbot.managers import RedisManager
from pajbot.streamhelper import StreamHelper

log = logging.getLogger(__name__)


class LogEntryTemplate:
    def __init__(self, message_fmt):
        self.message_fmt = message_fmt

    def get_message(self, *args):
        return self.message_fmt.format(*args)

class AdminLogManager:
    KEY = None
    TEMPLATES = {
            'Banphrase removed': LogEntryTemplate('Removed banphrase "{}"'),
            'Banphrase added': LogEntryTemplate('Added banphrase "{}"'),
            'Banphrase edited': LogEntryTemplate('Edited banphrase from "{}"'),
            'Banphrase toggled': LogEntryTemplate('{} banphrase "{}"'),
            'Module toggled': LogEntryTemplate('{} module "{}"'),
            'Module edited': LogEntryTemplate('Edited module "{}"'),
            'Timer toggled': LogEntryTemplate('{} timer "{}"'),
            }

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

    def post(type, source, *args, data={}):
        if type not in AdminLogManager.TEMPLATES:
            log.warn('{} has no template'.format(type))
            return False

        message = AdminLogManager.TEMPLATES[type].get_message(*args)
        AdminLogManager.add_entry(
                type, source,
                message,
                data=data)

        return True
