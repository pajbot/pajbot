from typing import Optional

import datetime
import logging

from pajbot import utils
from pajbot.managers.db import Base

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_utc import UtcDateTime

log = logging.getLogger("pajbot")


class PleblistSong(Base):
    __tablename__ = "pleblist_song"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stream_id: Mapped[int] = mapped_column(Integer, ForeignKey("stream.id", ondelete="CASCADE"), index=True)
    youtube_id: Mapped[str] = mapped_column(Text, index=True)
    date_added: Mapped[datetime.datetime] = mapped_column(UtcDateTime())
    date_played: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime())
    skip_after: Mapped[Optional[int]]
    user_id: Mapped[Optional[str]] = mapped_column(Text, ForeignKey("user.id", ondelete="SET NULL"))

    song_info = relationship(
        "PleblistSongInfo",
        uselist=False,
        primaryjoin="PleblistSongInfo.pleblist_song_youtube_id==PleblistSong.youtube_id",
        foreign_keys="PleblistSongInfo.pleblist_song_youtube_id",
        cascade="save-update,merge,expunge",
        lazy="joined",
    )

    def __init__(self, stream_id: int, youtube_id: str, **options) -> None:
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

    pleblist_song_youtube_id: Mapped[str] = mapped_column(Text, primary_key=True, autoincrement=False)
    title: Mapped[str]
    duration: Mapped[int]
    default_thumbnail: Mapped[str]

    def __init__(self, youtube_id: str, title: str, duration: int, default_thumbnail: str) -> None:
        self.pleblist_song_youtube_id = youtube_id
        self.title = title
        self.duration = duration
        self.default_thumbnail = default_thumbnail

    def jsonify(self):
        return {"title": self.title, "duration": self.duration, "default_thumbnail": self.default_thumbnail}
