import logging
from collections import UserDict
import datetime

from tyggbot.models.db import DBManager, Base
from tyggbot.models.time import TimeManager

import isodate
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy import orm
from sqlalchemy.orm import relationship
from apiclient.discovery import build
from apiclient.errors import HttpError

log = logging.getLogger('tyggbot')


class PleblistSong(Base):
    __tablename__ = 'tb_pleblist_song'

    id = Column(Integer, primary_key=True)
    stream_id = Column(Integer, ForeignKey('tb_stream.id'), index=True, nullable=False)
    youtube_id = Column(String(64, collation='utf8mb4_bin'), index=True, nullable=False)
    date_added = Column(DateTime, nullable=False)
    date_played = Column(DateTime, nullable=True)
    song_info = relationship('PleblistSongInfo', uselist=False)

    def __init__(self, stream_id, youtube_id):
        self.id = None
        self.stream_id = stream_id
        self.youtube_id = youtube_id
        self.date_added = datetime.datetime.now()
        self.date_played = None

    def jsonify(self):
        return {
                'id': self.id,
                'youtube_id': self.youtube_id,
                'info': self.song_info.jsonify() if self.song_info is not None else None
                }

class PleblistSongInfo(Base):
    __tablename__ = 'tb_pleblist_song_info'

    pleblist_song_youtube_id = Column(String(64, collation='utf8mb4_bin'), ForeignKey('tb_pleblist_song.youtube_id'), primary_key=True, autoincrement=False)
    title = Column(String(128), nullable=False)
    duration = Column(Integer, nullable=False)
    default_thumbnail = Column(String(256), nullable=False)

    def __init__(self, youtube_id, title, duration, default_thumbnail):
        self.pleblist_song_youtube_id = youtube_id
        self.title = title
        self.duration = duration
        self.default_thumbnail = default_thumbnail

    def jsonify(self):
        return {
                'title': self.title,
                'duration': self.duration,
                'default_thumbnail': self.default_thumbnail,
                }


class PleblistManager:
    youtube = None

    def init(developer_key):
        if PleblistManager.youtube is None:
            PleblistManager.youtube = build('youtube', 'v3', developerKey=developer_key)

    def create_pleblist_song_info(youtube_id):
        if PleblistManager.youtube is None:
            log.warning('youtube was not initialized')
            return False

        try:
            video_response = PleblistManager.youtube.videos().list(
                    id=str(youtube_id),
                    part='snippet,contentDetails'
                    ).execute()
        except HttpError as e:
            log.exception('???')
            log.info(e.content)
            log.info(e.resp)
            log.info(e.uri)

        log.debug(video_response)

        if len(video_response.get('items', [])) == 0:
            log.warning('FeelsBadMan')
            return False

        video = video_response['items'][0]

        title = video['snippet']['title']
        duration = int(isodate.parse_duration(video['contentDetails']['duration']).total_seconds())
        default_thumbnail = video['snippet']['thumbnails']['default']['url']

        return PleblistSongInfo(
                youtube_id,
                title,
                duration,
                default_thumbnail,
                )
