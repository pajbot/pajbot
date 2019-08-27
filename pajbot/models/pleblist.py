import logging

from sqlalchemy import Column, INT, TEXT
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy_utc import UtcDateTime

from pajbot import utils
from pajbot.managers.db import Base
from pajbot.managers.db import DBManager

log = logging.getLogger("pajbot")


class PleblistSong(Base):
    __tablename__ = "pleblist_song"

    id = Column(INT, primary_key=True)
    stream_id = Column(INT, ForeignKey("stream.id"), index=True, nullable=False)
    user_id = Column(INT, nullable=True)
    youtube_id = Column(TEXT, index=True, nullable=False)
    date_added = Column(UtcDateTime(), nullable=False)
    date_played = Column(UtcDateTime(), nullable=True)
    skip_after = Column(INT, nullable=True)
    song_info = relationship(
        "PleblistSongInfo",
        uselist=False,
        primaryjoin="PleblistSongInfo.pleblist_song_youtube_id==PleblistSong.youtube_id",
        foreign_keys="PleblistSongInfo.pleblist_song_youtube_id",
        cascade="save-update,merge,expunge",
        lazy="joined",
    )

    def __init__(self, stream_id, youtube_id, **options):
        self.id = None
        self.stream_id = stream_id
        self.user_id = options.get("user_id", None)
        self.youtube_id = youtube_id
        self.date_added = utils.now()
        self.date_played = None
        self.skip_after = options.get("skip_after", None)

        if self.skip_after is not None and self.skip_after < 0:
            # Make sure skip_after cannot be a negative number
            self.skip_after = None

    def jsonify(self):
        return {
            "id": self.id,
            "youtube_id": self.youtube_id,
            "skip_after": self.skip_after,
            "info": self.song_info.jsonify() if self.song_info is not None else None,
        }

    @property
    def link(self):
        return "youtu.be/{}".format(self.youtube_id)


class PleblistSongInfo(Base):
    __tablename__ = "pleblist_song_info"

    pleblist_song_youtube_id = Column(TEXT, primary_key=True, autoincrement=False)
    title = Column(TEXT, nullable=False)
    duration = Column(INT, nullable=False)
    default_thumbnail = Column(TEXT, nullable=False)

    def __init__(self, youtube_id, title, duration, default_thumbnail):
        self.pleblist_song_youtube_id = youtube_id
        self.title = title
        self.duration = duration
        self.default_thumbnail = default_thumbnail

    def jsonify(self):
        return {"title": self.title, "duration": self.duration, "default_thumbnail": self.default_thumbnail}


class PleblistManager:
    youtube = None

    @staticmethod
    def init(developer_key):
        if PleblistManager.youtube is None:
            import apiclient
            from apiclient.discovery import build

            def build_request(_, *args, **kwargs):
                import httplib2

                new_http = httplib2.Http()
                return apiclient.http.HttpRequest(new_http, *args, **kwargs)

            PleblistManager.youtube = build("youtube", "v3", developerKey=developer_key, requestBuilder=build_request)

    @staticmethod
    def get_song_info(youtube_id, db_session):
        return db_session.query(PleblistSongInfo).filter_by(pleblist_song_youtube_id=youtube_id).one_or_none()

    @staticmethod
    def create_pleblist_song_info(youtube_id):
        import isodate
        from apiclient.errors import HttpError

        if PleblistManager.youtube is None:
            log.warning("youtube was not initialized")
            return False

        try:
            video_response = (
                PleblistManager.youtube.videos().list(id=str(youtube_id), part="snippet,contentDetails").execute()
            )
        except HttpError as e:
            log.exception("Youtube HTTPError")
            log.info(e.content)
            log.info(e.resp)
            log.info(e.uri)
            return False
        except:
            log.exception("uncaught exception in videos().list()")
            return False

        if not video_response.get("items", []):
            log.warning("Got no valid responses for {}".format(youtube_id))
            return False

        video = video_response["items"][0]

        title = video["snippet"]["title"]
        duration = int(isodate.parse_duration(video["contentDetails"]["duration"]).total_seconds())
        default_thumbnail = video["snippet"]["thumbnails"]["default"]["url"]

        return PleblistSongInfo(youtube_id, title, duration, default_thumbnail)

    @staticmethod
    def get_current_song(stream_id):
        with DBManager.create_session_scope() as session:
            cur_song = (
                session.query(PleblistSong)
                .filter(PleblistSong.stream_id == stream_id, PleblistSong.date_played.is_(None))
                .order_by(PleblistSong.date_added.asc(), PleblistSong.id.asc())
                .first()
            )
            if cur_song is None:
                return None
            session.expunge(cur_song)
            return cur_song
