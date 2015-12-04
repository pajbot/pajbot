import logging
from collections import UserDict
import datetime

from tyggbot.models.db import DBManager, Base
from tyggbot.models.time import TimeManager

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy import orm

log = logging.getLogger('tyggbot')


class PleblistSong(Base):
    __tablename__ = 'tb_pleblist_song'

    id = Column(Integer, primary_key=True)
    stream_id = Column(Integer, ForeignKey('tb_stream.id'), index=True, nullable=False)
    youtube_id = Column(String(64), nullable=False)
    date_added = Column(DateTime, nullable=False)
    date_played = Column(DateTime, nullable=True)

    def __init__(self, stream_id, youtube_id):
        self.id = None
        self.stream_id = stream_id
        self.youtube_id = youtube_id
        self.date_added = datetime.datetime.now()
        self.date_played = None
