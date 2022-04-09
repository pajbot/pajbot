import logging

from pajbot import utils
from pajbot.managers.db import Base

from sqlalchemy import INT, TEXT, Column, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy_utc import UtcDateTime

log = logging.getLogger("pajbot")


class PleblistSong(Base):
    __tablename__ = "pleblist_song"

    id = Column(INT, primary_key=True)
    stream_id = Column(INT, ForeignKey("stream.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = Column(INT, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
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
        return f"youtu.be/{self.youtube_id}"


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
