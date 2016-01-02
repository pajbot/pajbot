import logging
from collections import UserDict

from pajbot.models.db import DBManager, Base

from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.mysql import TEXT

log = logging.getLogger('pajbot')


class Setting(Base):
    __tablename__ = 'tb_settings'

    id = Column(Integer, primary_key=True)
    setting = Column(String(128))
    value = Column(TEXT)
    type = Column(String(32))

    def __init__(self, setting, value, type):
        self.id = None
        self.setting = setting
        self.value = value
        self.type = type

    def parse_value(self):
        try:
            if self.type == 'int':
                return int(self.value)
            elif self.type == 'string':
                return self.value
            elif self.type == 'list':
                return self.value.split(',')
            elif self.type == 'bool':
                return int(self.value) == 1
            else:
                log.error('Invalid setting type: {0}'.format(self.type))
        except Exception:
            log.exception('Exception caught when loading setting')

        return None


class SettingManager(UserDict):
    def __init__(self, overrides={}):
        UserDict.__init__(self)
        self.db_session = DBManager.create_session()
        self.default_settings = {
                'broadcaster': 'test_broadcaster',
                'ban_ascii': True,
                'lines_offline': True,
                'parse_pyramids': False,
                'parse_emote_combo': False,
                'check_links': True,
                'warnings_enabled': True,
                'warnings_total_chances': 2,
                'warnings_redis_prefix': '',
                'warnings_length': 600,
                'warnings_base_timeout': 10,
                }
        self.default_settings.update(overrides)

    def commit(self):
        self.db_session.commit()

    def reload(self):
        self.data = self.default_settings
        for setting in self.db_session.query(Setting):
            parsed_value = setting.parse_value()
            if parsed_value is not None:
                self.data[setting.setting] = setting.parse_value()

        return self
