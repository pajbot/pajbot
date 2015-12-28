import logging
from collections import UserDict
import datetime

from pajbot.models.db import DBManager, Base
from pajbot.models.time import TimeManager

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy import orm
from sqlalchemy.orm import relationship

log = logging.getLogger('pajbot')


class PleblistSong(Base):
    __tablename__ = 'tb_pleblist_song'

    id = Column(Integer, primary_key=True)
    stream_id = Column(Integer, ForeignKey('tb_stream.id'), index=True, nullable=False)
    youtube_id = Column(String(64, collation='utf8mb4_bin'), index=True, nullable=False)
    date_added = Column(DateTime, nullable=False)
    date_played = Column(DateTime, nullable=True)
    song_info = relationship('PleblistSongInfo',
            uselist=False,
            primaryjoin='PleblistSongInfo.pleblist_song_youtube_id==PleblistSong.youtube_id',
            foreign_keys='PleblistSongInfo.pleblist_song_youtube_id',
            cascade='save-update,merge,expunge',
            lazy='joined')

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

    @property
    def link(self):
        return 'youtu.be/{}'.format(self.youtube_id)

class PleblistSongInfo(Base):
    __tablename__ = 'tb_pleblist_song_info'

    pleblist_song_youtube_id = Column(String(64, collation='utf8mb4_bin'), primary_key=True, autoincrement=False)
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
            from apiclient.discovery import build
            PleblistManager.youtube = build('youtube', 'v3', developerKey=developer_key)

    def create_pleblist_song_info(youtube_id):
        import isodate
        from apiclient.errors import HttpError

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

    def get_current_song(stream_id):
        with DBManager.create_session_scope() as session:
            cur_song = session.query(PleblistSong).filter(PleblistSong.stream_id == stream_id, PleblistSong.date_played.is_(None)).order_by(PleblistSong.date_added.asc()).first()
            if cur_song is None:
                return None
            session.expunge(cur_song)
            return cur_song
