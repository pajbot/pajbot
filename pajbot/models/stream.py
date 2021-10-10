import logging

from typing import Any, Dict, List, Optional, Union

from sqlalchemy import BOOLEAN, INT, TEXT
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy_utc import UtcDateTime

from pajbot import utils
from pajbot.apiwrappers.base import BaseAPI
from pajbot.apiwrappers.twitch.base import BaseTwitchAPI
from pajbot.apiwrappers.twitch.helix import TwitchVideo, TwitchGame
from pajbot.managers.db import Base
from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.managers.redis import RedisManager

from pajbot.models.user import UserStream, UserChannelInformation

log = logging.getLogger("pajbot")


class StreamChunk(Base):
    __tablename__ = "stream_chunk"

    id = Column(INT, primary_key=True)
    stream_id = Column(INT, ForeignKey("stream.id", ondelete="CASCADE"), nullable=False)
    broadcast_id = Column(TEXT, nullable=False)
    video_url = Column(TEXT, nullable=True)
    video_preview_image_url = Column(TEXT, nullable=True)
    chunk_start = Column(UtcDateTime(), nullable=False)
    chunk_end = Column(UtcDateTime(), nullable=True)

    def __init__(self, stream, broadcast_id, created_at, **options):
        self.id = None
        self.stream_id = stream.id
        self.broadcast_id = broadcast_id
        self.video_url = None
        self.video_preview_image_url = None
        self.chunk_start = BaseTwitchAPI.parse_datetime(created_at)
        self.chunk_end = None

        self.stream = stream


class Stream(Base):
    __tablename__ = "stream"

    id = Column(INT, primary_key=True)
    title = Column(TEXT, nullable=False)
    stream_start = Column(UtcDateTime(), nullable=False)
    stream_end = Column(UtcDateTime(), nullable=True)
    ended = Column(BOOLEAN, nullable=False, default=False)

    stream_chunks = relationship(
        StreamChunk, uselist=True, backref="stream", cascade="save-update, merge, expunge", lazy="joined"
    )

    def __init__(self, created_at, **options):
        self.id = None
        self.title = options.get("title", "NO TITLE")
        self.stream_start = BaseAPI.parse_datetime(created_at)
        self.stream_end = None
        self.ended = False

    @property
    def uptime(self):
        """
        Returns a TimeDelta for how long the stream was online, or is online.
        """

        if self.ended is False:
            return utils.now() - self.stream_start

        return self.stream_end - self.stream_start


class StreamManager:
    NUM_OFFLINES_REQUIRED = 10
    CHANNEL_INFORMATION_CHECK_INTERVAL = 120  # seconds (Every 2 minutes)
    STATUS_CHECK_INTERVAL = 20  # seconds (Every 20 seconds)
    VIDEO_URL_CHECK_INTERVAL = 300  # seconds (Every 5 minutes)

    def fetch_video_url_stage1(self) -> None:
        if self.online is False:
            return

        data = self.bot.twitch_helix_api.get_videos_by_user_id(self.bot.streamer_user_id)
        self.bot.execute_now(self.refresh_video_url_stage2, data)

    def fetch_video_url_stage2(self, data: List[TwitchVideo]) -> Optional[TwitchVideo]:
        if self.current_stream_chunk is None:
            # Nothing to update
            return None

        if self.current_stream_chunk.video_url is not None:
            # Stream chunk already has a video url
            return None

        try:
            for video in data:
                recorded_at = BaseTwitchAPI.parse_datetime(video.created_at)
                time_diff = self.current_stream_chunk.chunk_start - recorded_at
                if abs(time_diff.total_seconds()) < 60 * 5:
                    # we found the relevant video!
                    return video
        except:
            log.exception("Uncaught exception in fetch_video_url")

        return None

    def __init__(self, bot):
        self.bot = bot

        self.current_stream_chunk: Optional[StreamChunk] = None  # should this even exist?
        self.current_stream: Optional[Stream] = None

        self.num_offlines: int = 0
        self.first_offline = None

        self.num_viewers: int = 0

        self.game: str = "Loading..."
        self.title: str = "Loading..."

        # Polls Helix's "Get Channel Information" endpoint and updates the StreamManagers game name & title
        # Works if stream is online or offline
        self.bot.execute_every(
            self.CHANNEL_INFORMATION_CHECK_INTERVAL,
            self.bot.action_queue.submit,
            self.refresh_channel_information,
        )

        self.bot.execute_now(
            self.bot.action_queue.submit,
            self.refresh_channel_information,
        )

        # Polls Helix's "Get Streams" endpoint and updates the liveness of the stream.
        # If the stream is live, we also update some data such as title and stream id
        self.bot.execute_every(
            self.STATUS_CHECK_INTERVAL, self.bot.action_queue.submit, self.refresh_stream_status_stage1
        )
        self.bot.execute_every(
            self.VIDEO_URL_CHECK_INTERVAL, self.bot.action_queue.submit, self.refresh_video_url_stage1
        )

        # This will load the latest stream so we can post an accurate "time since last online" figure.
        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            self.current_stream = (
                db_session.query(Stream).filter_by(ended=False).order_by(Stream.stream_start.desc()).first()
            )
            self.last_stream = db_session.query(Stream).filter_by(ended=True).order_by(Stream.stream_end.desc()).first()
            if self.current_stream:
                self.current_stream_chunk = (
                    db_session.query(StreamChunk)
                    .filter_by(stream_id=self.current_stream.id)
                    .order_by(StreamChunk.chunk_start.desc())
                    .first()
                )
                log.info(f"Set current stream chunk here to {self.current_stream_chunk}")
            db_session.expunge_all()

    @property
    def online(self):
        return self.current_stream is not None

    @property
    def offline(self):
        return self.current_stream is None

    @staticmethod
    def commit():
        log.info("commiting something?")

    def create_stream_chunk(self, status: UserStream):
        if self.current_stream is None:
            log.warn("create_stream_chunk called with current_stream being None")
            return

        if self.current_stream_chunk is not None:
            # There's already a stream chunk started!
            self.current_stream_chunk.chunk_end = utils.now()
            DBManager.session_add_expunge(self.current_stream_chunk)

        stream_chunk: Optional[StreamChunk] = None

        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            stream_chunk = db_session.query(StreamChunk).filter_by(broadcast_id=status.id).one_or_none()
            if stream_chunk is None:
                log.info("Creating stream chunk, from create_stream_chunk")
                stream_chunk = StreamChunk(self.current_stream, status.id, status.started_at)
                self.current_stream_chunk = stream_chunk
                db_session.add(stream_chunk)
                db_session.commit()
            else:
                log.info("We already have a stream chunk!")
                self.current_stream_chunk = stream_chunk
                stream_chunk = None
            db_session.expunge_all()

        if stream_chunk:
            self.current_stream.stream_chunks.append(stream_chunk)

    def create_stream(self, status: UserStream) -> None:
        log.info("Attempting to create a stream!")
        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            stream_chunk = db_session.query(StreamChunk).filter_by(broadcast_id=status.id).one_or_none()
            new_stream = False
            if stream_chunk is not None:
                stream = stream_chunk.stream
            else:
                log.info("checking if there is an active stream already")
                stream = db_session.query(Stream).filter_by(ended=False).order_by(Stream.stream_start.desc()).first()
                new_stream = stream is None

                if new_stream:
                    log.info("No active stream, create new!")
                    stream = Stream(status.started_at, title=status.title)
                    db_session.add(stream)
                    db_session.commit()
                    log.info("Successfully added stream!")
                stream_chunk = StreamChunk(stream, status.id, status.started_at)
                db_session.add(stream_chunk)
                db_session.commit()
                stream.stream_chunks.append(stream_chunk)
                log.info("Created stream chunk")

            self.current_stream = stream
            self.current_stream_chunk = stream_chunk
            db_session.expunge_all()

            if new_stream:
                HandlerManager.trigger("on_stream_start", stop_on_false=False)

            log.info("Successfully created a stream")

    def go_offline(self) -> None:
        if self.current_stream is None or self.current_stream_chunk is None:
            return

        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            self.current_stream.ended = True
            self.current_stream.stream_end = self.first_offline
            self.current_stream_chunk.chunk_end = self.first_offline

            db_session.add(self.current_stream)
            db_session.add(self.current_stream_chunk)

            db_session.commit()

            db_session.expunge_all()

        self.last_stream = self.current_stream
        self.current_stream = None
        self.current_stream_chunk = None

        HandlerManager.trigger("on_stream_stop", stop_on_false=False)

    def refresh_channel_information(self) -> None:
        channel_information: Optional[UserChannelInformation] = self.bot.twitch_helix_api.get_channel_information(
            self.bot.streamer_user_id
        )

        if channel_information is None:
            log.error(f"Unable to fetch channel information about {self.bot.streamer_user_id}")
            return

        redis = RedisManager.get()
        key_prefix = self.bot.streamer + ":"

        stream_data: Dict[Union[bytes, str], Any] = {
            f"{key_prefix}game": channel_information.game_name,
            f"{key_prefix}title": channel_information.title,
        }

        redis.hmset("stream_data", stream_data)

        self.game = channel_information.game_name
        self.title = channel_information.title

    def refresh_stream_status_stage1(self) -> None:
        status: Optional[UserStream] = self.bot.twitch_helix_api.get_stream_by_user_id(self.bot.streamer_user_id)
        self.bot.execute_now(self.refresh_stream_status_stage2, status)

    def refresh_stream_status_stage2(self, status: Optional[UserStream]) -> None:
        redis = RedisManager.get()
        key_prefix = self.bot.streamer + ":"

        # Default data we want to update in case the stream is offline
        stream_data: Dict[Union[bytes, str], Any] = {
            f"{key_prefix}online": "False",
            f"{key_prefix}viewers": 0,
        }
        self.num_viewers = 0

        if status:
            # Update stream_data with fresh online data
            stream_data[f"{key_prefix}online"] = "True"
            stream_data[f"{key_prefix}viewers"] = status.viewer_count

            game_info: Optional[TwitchGame] = self.bot.twitch_helix_api.get_game_by_game_id(status.game_id)
            game_name: str = ""
            if game_info is not None:
                game_name = game_info.name

            stream_data[f"{key_prefix}game"] = game_name

            self.num_viewers = status.viewer_count
            self.game = game_name
            self.title = status.title

            self.num_offlines = 0
            self.first_offline = None

            # Update stream chunk data
            if self.current_stream is None:
                self.create_stream(status)
            if self.current_stream_chunk is None:
                self.create_stream_chunk(status)
            if self.current_stream_chunk is not None:
                if self.current_stream_chunk.broadcast_id != status.id:
                    log.debug(f"Detected a new chunk! {self.current_stream_chunk.broadcast_id} != {status.id}")
                    self.create_stream_chunk(status)
        else:
            # stream reported as offline
            if self.online is True:
                # but we have stream marked as online.. begin the countdown
                self.num_offlines += 1
                log.info(f"Offline. {self.num_offlines}")
                if self.first_offline is None:
                    self.first_offline = utils.now()

                if self.num_offlines >= self.NUM_OFFLINES_REQUIRED:
                    log.info("Switching to offline state!")
                    self.go_offline()

        redis.hmset("stream_data", stream_data)

    def refresh_video_url_stage1(self) -> None:
        self.fetch_video_url_stage1()

    def refresh_video_url_stage2(self, data) -> None:
        if self.online is False:
            return

        if self.current_stream_chunk is None or self.current_stream is None:
            return

        video: Optional[TwitchVideo] = self.fetch_video_url_stage2(data)

        if video is None:
            return

        log.info(f"Successfully fetched a video url: {video.url}")
        if self.current_stream_chunk is None or self.current_stream_chunk.video_url is None:
            with DBManager.create_session_scope(expire_on_commit=False) as db_session:
                self.current_stream_chunk.video_url = video.url
                self.current_stream_chunk.video_preview_image_url = video.thumbnail_url

                db_session.add(self.current_stream_chunk)

                db_session.commit()

                db_session.expunge_all()
            log.info("Successfully commited video url data.")
        elif self.current_stream_chunk.video_url != video.url:
            # End current stream chunk
            self.current_stream_chunk.chunk_end = utils.now()
            DBManager.session_add_expunge(self.current_stream_chunk)

            with DBManager.create_session_scope(expire_on_commit=False) as db_session:
                stream_chunk = StreamChunk(
                    self.current_stream, self.current_stream_chunk.broadcast_id, video.created_at
                )
                self.current_stream_chunk = stream_chunk
                self.current_stream_chunk.video_url = video.url
                self.current_stream_chunk.video_preview_image_url = video.thumbnail_url

                db_session.add(self.current_stream_chunk)

                db_session.commit()

                db_session.expunge_all()
            log.info("Successfully commited video url data in a new chunk.")

    def get_stream_value(self, key: str, extra: Dict[str, Any] = {}) -> Optional[Any]:
        return getattr(self, key, None)

    def get_current_stream_value(self, key: str, extra: Dict[str, Any] = {}) -> Optional[Any]:
        if self.current_stream is not None:
            return getattr(self.current_stream, key, None)

        return None

    def get_last_stream_value(self, key: str, extra: Dict[str, Any] = {}) -> Optional[Any]:
        if self.last_stream is not None:
            return getattr(self.last_stream, key, None)

        return None
