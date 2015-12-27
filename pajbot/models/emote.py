import logging
import datetime
from collections import UserDict
import re

from pajbot.models.db import DBManager, Base

from sqlalchemy import orm
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

log = logging.getLogger('pajbot')


class Emote(Base):
    __tablename__ = 'tb_emote'

    id = Column(Integer, primary_key=True)
    emote_id = Column(Integer, nullable=True)  # twitch.tv Emote ID
    emote_hash = Column(String(32), nullable=True)  # BTTV Emote Hash
    code = Column(String(length=64, collation='utf8mb4_bin'), nullable=False, index=True)

    stats = relationship('EmoteStats', uselist=False)

    def __init__(self, manager, emote_id=None, emote_hash=None, code=None):
        self.manager = manager
        self.id = None
        self.emote_id = emote_id
        self.emote_hash = emote_hash
        self.code = code  # This value will be inserted when the update_emotes script is called, if necessary.

        if self.emote_id is None:
            self.regex = re.compile('(?<![^ ]){0}(?![^ ])'.format(re.escape(self.code)))
        else:
            self.regex = None

    @orm.reconstructor
    def init_on_load(self):
        if self.emote_id is None:
            self.regex = re.compile('(?<![^ ]){0}(?![^ ])'.format(re.escape(self.code)))
        else:
            self.regex = None

    @property
    def count(self):
        return self.stats.count if self.stats is not None else 0

    @property
    def tm(self):
        return self.stats.tm if self.stats is not None else 0

    @property
    def tm_record(self):
        return self.stats.tm_record if self.stats is not None else 0

    def add(self, count, reactor):
        if self.stats is None:
            self.stats = self.manager.db_session.query(EmoteStats).filter_by(emote_code=self.code).one_or_none()
            if self.stats is None:
                self.stats = EmoteStats(self.code)
                self.manager.db_session.add(self.stats)

        self.stats.add(count, reactor)


class EmoteStats(Base):
    __tablename__ = 'tb_emote_stats'

    emote_code = Column(String(length=64, collation='utf8mb4_bin'), ForeignKey('tb_emote.code'), primary_key=True, autoincrement=False)
    tm_record = Column(Integer, nullable=False, default=0)
    tm_record_date = Column(DateTime, nullable=True)
    count = Column(Integer, nullable=False, default=0)

    def __init__(self, emote_code):
        self.emote_code = emote_code
        self.tm_record = 0
        self.tm_record_date = None
        self.count = 0

        self.tm = 0

    @orm.reconstructor
    def init_on_load(self):
        self.tm = 0

    def add(self, count, reactor):
        self.count += count
        self.tm += count
        if self.tm > self.tm_record:
            self.tm_record = self.tm
            self.tm_record_date = datetime.datetime.now()

        reactor.execute_delayed(60, self.reduce, (count, ))

    def reduce(self, count):
        self.tm -= count


class BTTVEmoteManager:
    def __init__(self, emote_manager):
        from pajbot.apiwrappers import BTTVApi
        self.emote_manager = emote_manager
        self.bttv_api = BTTVApi()
        self.channel_emotes = []

    def update_emotes(self):
        log.debug('Updating BTTV Emotes...')
        global_emotes = self.bttv_api.get_global_emotes()
        channel_emotes = self.bttv_api.get_channel_emotes(self.emote_manager.streamer)

        self.channel_emotes = [emote['code'] for emote in channel_emotes]

        self.emote_manager.bot.mainthread_queue.add(self._add_bttv_emotes,
                                                    args=[global_emotes + channel_emotes])

    def _add_bttv_emotes(self, emotes):
        for emote in emotes:
            key = 'custom_{}'.format(emote['code'])
            if key in self.emote_manager.data:
                self.emote_manager.data[key].emote_hash = emote['emote_hash']
            else:
                self.emote_manager.add_emote(**emote)
        log.debug('Added {} emotes'.format(len(emotes)))


class EmoteManager(UserDict):
    def __init__(self, bot):
        UserDict.__init__(self)
        self.bot = bot
        self.streamer = bot.streamer
        self.db_session = DBManager.create_session()
        self.custom_data = []
        self.bttv_emote_manager = BTTVEmoteManager(self)

        self.bot.execute_delayed(5, self.bot.action_queue.add, (self.bttv_emote_manager.update_emotes, ))
        self.bot.execute_every(60 * 60 * 2, self.bot.action_queue.add, (self.bttv_emote_manager.update_emotes, ))

    def commit(self):
        self.db_session.commit()

    def reload(self):
        self.data = {}
        self.custom_data = []

        num_emotes = 0
        for emote in self.db_session.query(Emote):
            emote.manager = self
            num_emotes += 1
            self.add_to_data(emote)

        log.info('Loaded {0} emotes'.format(num_emotes))
        return self

    def add_emote(self, emote_id=None, emote_hash=None, code=None):
        emote = Emote(self, emote_id=emote_id, emote_hash=emote_hash, code=code)
        self.add_to_data(emote)
        self.db_session.add(emote)
        return emote

    def add_to_data(self, emote):
        if emote.emote_id:
            self.data[emote.emote_id] = emote
            if emote.code:
                self.data[emote.code] = emote
        else:
            self.custom_data.append(emote)
            if emote.code:
                self.data['custom_' + emote.code] = emote

    def __getitem__(self, key):
        if key not in self.data:
            try:
                # We can only dynamically add emotes that are ID-based
                value = int(key)
            except ValueError:
                return None

            log.info('Adding new emote with ID {0}'.format(value))
            self.add_emote(emote_id=value)

        return self.data[key]

    def find(self, key):
        log.info('Finding emote with key {0}'.format(key))
        try:
            emote_id = int(key)
        except ValueError:
            emote_id = None

        if emote_id:
            return self.data[emote_id]
        else:
            key = str(key)
            if len(key) > 0 and key[0] == ':':
                key = key.upper()
            if key in self.data:
                return self.data[key]
            else:
                for emote in self.custom_data:
                    if emote.code == key:
                        return emote

        return None
