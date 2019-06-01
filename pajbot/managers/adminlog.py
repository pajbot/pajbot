import json
import logging

import pajbot.utils
from pajbot.managers.redis import RedisManager
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
        "Banphrase added": LogEntryTemplate('Added banphrase "{}"'),
        "Banphrase edited": LogEntryTemplate('Edited banphrase from "{}"'),
        "Banphrase removed": LogEntryTemplate('Removed banphrase "{}"'),
        "Banphrase toggled": LogEntryTemplate('{} banphrase "{}"'),
        "Blacklist link added": LogEntryTemplate('Added blacklist link "{}"'),
        "Blacklist link removed": LogEntryTemplate('Removed blacklisted link "{}"'),
        "Module edited": LogEntryTemplate('Edited module "{}"'),
        "Module toggled": LogEntryTemplate('{} module "{}"'),
        "Timer added": LogEntryTemplate('Added timer "{}"'),
        "Timer removed": LogEntryTemplate('Removed timer "{}"'),
        "Timer toggled": LogEntryTemplate('{} timer "{}"'),
        "Whitelist link added": LogEntryTemplate('Added whitelist link "{}"'),
        "Whitelist link removed": LogEntryTemplate('Removed whitelisted link "{}"'),
    }

    @staticmethod
    def get_key():
        if AdminLogManager.KEY is None:
            streamer = StreamHelper.get_streamer()
            AdminLogManager.KEY = "{streamer}:logs:admin".format(streamer=streamer)
        return AdminLogManager.KEY

    @staticmethod
    def add_entry(entry_type, source, message, data={}):
        redis = RedisManager.get()

        payload = {
            "type": entry_type,
            "user_id": source.id,
            "message": message,
            "created_at": str(pajbot.utils.now().strftime("%Y-%m-%d %H:%M:%S %Z")),
            "data": data,
        }

        redis.lpush(AdminLogManager.get_key(), json.dumps(payload))

    @staticmethod
    def get_entries(offset=0, limit=50):
        redis = RedisManager.get()

        entries = []

        for entry in redis.lrange(AdminLogManager.get_key(), offset, limit):
            try:
                entries.append(json.loads(entry))
            except:
                log.exception("babyrage")

        return entries

    @staticmethod
    def post(entry_type, source, *args, data={}):
        if entry_type not in AdminLogManager.TEMPLATES:
            log.warning("{} has no template".format(type))
            return False

        message = AdminLogManager.TEMPLATES[entry_type].get_message(*args)
        AdminLogManager.add_entry(entry_type, source, message, data=data)

        return True
