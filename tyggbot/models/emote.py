import logging
from collections import UserDict
import re

from tyggbot.models.db import DBManager, Base

from sqlalchemy import orm
from sqlalchemy import Column, Integer, String

log = logging.getLogger('tyggbot')


class Emote(Base):
    __tablename__ = 'tb_emote'

    id = Column(Integer, primary_key=True)
    emote_id = Column(Integer)  # twitch.tv Emote ID
    emote_hash = Column(String(32))  # BTTV Emote Hash
    code = Column(String(64))
    tm_record = Column(Integer)
    count = Column(Integer)

    def __init__(self, emote_id=None, emote_hash=None, code=None):
        self.id = None
        self.emote_id = emote_id
        self.emote_hash = emote_hash
        self.code = code  # This value will be inserted when the update_emotes script is called, if necessary.
        self.tm_record = 0
        self.count = 0

        self.tm = 0
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

        self.tm = 0

    def add(self, count, reactor):
        self.count += count
        self.tm += count
        if self.tm > self.tm_record:
            self.tm_record = self.tm

        reactor.execute_delayed(60, self.reduce, (count, ))

    def reduce(self, count):
        self.tm -= count


class BTTVEmoteManager:
    def __init__(self, emote_manager):
        from tyggbot.apiwrappers import BTTVApi
        self.emote_manager = emote_manager
        self.bttv_api = BTTVApi()

    def update_emotes(self):
        log.debug('Updating BTTV Emotes...')
        emotes = self.bttv_api.get_global_emotes()
        emotes += self.bttv_api.get_channel_emotes(self.emote_manager.streamer)

        self.emote_manager.bot.mainthread_queue.add(self._add_bttv_emotes,
                                                    args=[emotes])

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

        self.bot.execute_every(60 * 60 * 2, self.bot.action_queue.add, (self.bttv_emote_manager.update_emotes, ))

    def commit(self):
        self.db_session.commit()

    def reload(self):
        self.data = {}
        self.custom_data = []

        num_emotes = 0
        for emote in self.db_session.query(Emote):
            num_emotes += 1
            self.add_to_data(emote)

        log.info('Loaded {0} emotes'.format(num_emotes))
        return self

    def add_emote(self, emote_id=None, emote_hash=None, code=None):
        emote = Emote(emote_id=emote_id, emote_hash=emote_hash, code=code)
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
            if key in self.data:
                return self.data[key]
            else:
                for emote in self.custom_data:
                    if emote.code == key:
                        return emote

        return None
