import datetime
import logging
import re

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import reconstructor
from sqlalchemy.orm import relationship

from pajbot.managers import Base

log = logging.getLogger(__name__)


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

    @reconstructor
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

    @reconstructor
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
