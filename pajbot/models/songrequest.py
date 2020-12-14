import logging

from sqlalchemy import Column, INT, TEXT, BOOLEAN, REAL
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy_utc import UtcDateTime

from pajbot import utils
from pajbot.managers.db import Base
from pajbot.managers.songrequest_queue_manager import SongRequestQueueManager
from pajbot.streamhelper import StreamHelper

log = logging.getLogger("pajbot")


class SongrequestQueue(Base):
    __tablename__ = "songrequest_queue"

    id = Column(INT, primary_key=True)
    video_id = Column(TEXT, ForeignKey("songrequest_song_info.video_id", ondelete="CASCADE"), nullable=False)
    date_added = Column(UtcDateTime(), nullable=False)
    skip_after = Column(INT, nullable=True)  # skipped after
    requested_by_id = Column(INT, ForeignKey("user.id"), nullable=True)
    date_resumed = Column(UtcDateTime(), nullable=True)
    played_for = Column(REAL, default=0, nullable=False)
    song_info = relationship("SongRequestSongInfo", foreign_keys=[video_id], lazy="joined")
    requested_by = relationship("User", foreign_keys=[requested_by_id], lazy="joined")

    def __init__(self, **options):
        super().__init__(**options)
        if self.skip_after and self.skip_after < 0:
            # Make sure skip_after cannot be a negative number
            self.skip_after = None

    def jsonify(self):
        return {
            "id": self.id,
            "video_id": self.video_id,
            "date_added": self.date_added,
            "skip_after": self.skip_after,
            "playing": self.playing,
            "current_song_time": self.current_song_time,
            "requested_by": self.requested_by.username_raw if self.requested_by_id else None,
        }

    def webjsonify(self):
        return {
            "song_info": self.song_info.jsonify(),
            "requested_by": self.requested_by.username_raw if self.requested_by_id else "Backup Playlist",
            "current_song_time": self.current_song_time,
            "database_id": self.id,
            "skip_after": self.skip_after,
            "formatted_duration": self.formatted_duration,
        }

    def purge(self, db_session):
        SongRequestQueueManager.remove_song_id(self.id)
        db_session.delete(self)

    @property
    def formatted_duration(self):
        m, s = divmod(self.duration, 60)
        m = int(m)
        s = int(s)
        return f"{m:02d}:{s:02d}"

    def queue_and_playing_in(self, db_session):
        all_song_ids_before_current = SongRequestQueueManager.songs_before(self.id, "song-queue")
        if SongRequestQueueManager.song_playing_id:
            all_song_ids_before_current.append(SongRequestQueueManager.song_playing_id)
        queued_unordered_songs = SongrequestQueue.from_list_id(db_session, all_song_ids_before_current)
        time = 0
        for song in queued_unordered_songs:
            time += song.time_left if song.playing else song.duration
            if song.playing:
                log.info(f"Song has {song.time_left}")
        return len(queued_unordered_songs), time

    @hybrid_property
    def playing(self):
        return str(self.id) == str(SongRequestQueueManager.song_playing_id)

    @hybrid_property
    def time_left(self):
        time_left = self.duration - self.current_song_time
        return time_left if time_left > 0 else 0

    @hybrid_property
    def current_song_time(self):
        return (
            self.played_for + ((utils.now() - self.date_resumed).total_seconds() if self.date_resumed else 0)
            if bool(self.playing)
            else 0
        )

    @hybrid_property
    def duration(self):
        return self.skip_after if self.skip_after else self.song_info.duration

    def move_song(self, to_id):
        if not self.requested_by:
            return

        SongRequestQueueManager.move_song(self.id, to_id)

    def to_histroy(self, db_session, skipped_by_id=None):
        stream_id = StreamHelper.get_current_stream_id()
        history = SongrequestHistory.create(
            db_session,
            stream_id or None,
            self.video_id,
            self.requested_by.id if self.requested_by else None,
            skipped_by_id,
            self.skip_after,
        )
        self.purge(db_session)
        return history

    @hybrid_property
    def link(self):
        return f"youtu.be/{self.video_id}"

    @staticmethod
    def from_list_id(db_session, _ids):
        return db_session.query(SongrequestQueue).populate_existing().filter(SongrequestQueue.id.in_(_ids)).all()

    @staticmethod
    def from_id(db_session, _id):
        return db_session.query(SongrequestQueue).populate_existing().filter_by(id=_id).one_or_none()

    @staticmethod
    def pop_next_song(db_session, use_backup=True):
        song = None
        while song is None:
            next_id = SongRequestQueueManager.get_next_song(use_backup)
            SongRequestQueueManager.remove_song_id(next_id)
            if not next_id:
                return None

            song = db_session.query(SongrequestQueue).populate_existing().filter_by(id=next_id).one_or_none()
        return song

    @staticmethod
    def create(db_session, video_id, skip_after, requested_by_id, queue=None, backup=False):
        songrequestqueue = SongrequestQueue(
            video_id=video_id, date_added=utils.now(), skip_after=skip_after, requested_by_id=requested_by_id
        )
        db_session.add(songrequestqueue)
        db_session.commit()
        SongRequestQueueManager.inset_song(songrequestqueue.id, "backup-song-queue" if backup else "song-queue", queue)
        return songrequestqueue

    @staticmethod
    def get_current_song(db_session):
        return (
            db_session.query(SongrequestQueue)
            .populate_existing()
            .filter_by(id=SongRequestQueueManager.song_playing_id)
            .one_or_none()
            if SongRequestQueueManager.song_playing_id
            else None
        )

    @staticmethod
    def get_next_song(db_session):
        song = None
        while song is None:
            next_id = SongRequestQueueManager.get_next_song()
            if not next_id:
                return None

            song = db_session.query(SongrequestQueue).populate_existing().filter_by(id=next_id).one_or_none()
            if not song:
                SongRequestQueueManager.remove_song_id(next_id)
        return song

    @staticmethod
    def all_by_video_id(db_session, _video_id):
        return db_session.query(SongrequestQueue).populate_existing().filter_by(video_id=_video_id).all()

    @staticmethod
    def pruge_videos(db_session, _video_id):
        all_songs = SongrequestQueue.all_by_video_id(db_session, _video_id)
        for song in all_songs:
            song.purge(db_session)

    @staticmethod
    def clear_backup_songs(db_session):
        SongRequestQueueManager.delete_backup_songs()
        return db_session.query(SongrequestQueue).filter_by(requested_by=None).delete(synchronize_session="evaluate")

    @staticmethod
    def load_backup_songs(db_session, songs, youtube):
        for song in songs:
            song_info = SongRequestSongInfo.create_or_get(db_session, song, youtube)
            if song_info:
                SongrequestQueue.create(db_session, song, None, None, backup=True)

    @staticmethod
    def get_playlist(db_session, limit=None, as_json=True):
        while True:
            queued_song_ids = SongRequestQueueManager.get_next_songs(limit=limit, queue="song-queue")
            if not queued_song_ids:
                return []

            queued_unordered_songs = SongrequestQueue.from_list_id(db_session, queued_song_ids)
            if len(queued_song_ids) == len(queued_unordered_songs):
                break
            song_ids = [song.id for song in queued_unordered_songs]
            for song_id in queued_song_ids:
                if song_id not in song_ids:
                    SongRequestQueueManager.remove_song_id(song_id)

        queued_songs = SongrequestQueue.sort(queued_song_ids, queued_unordered_songs)
        if not as_json:
            return queued_songs

        songs = []
        for song in queued_songs:
            songs.append(song.webjsonify())
        return songs

    @staticmethod
    def get_backup_playlist(db_session, limit=None, as_json=True):
        while True:
            queued_song_ids = SongRequestQueueManager.get_next_songs(limit=limit, queue="backup-song-queue")
            if not queued_song_ids:
                return []

            queued_unordered_songs = SongrequestQueue.from_list_id(db_session, queued_song_ids)
            if len(queued_song_ids) == len(queued_unordered_songs):
                break
            song_ids = [song.id for song in queued_unordered_songs]
            for song_id in queued_song_ids:
                if song_id not in song_ids:
                    SongRequestQueueManager.remove_song_id(song_id)

        queued_songs = SongrequestQueue.sort(queued_song_ids, queued_unordered_songs)
        if not as_json:
            return queued_songs

        songs = []
        for song in queued_songs:
            songs.append(song.webjsonify())
        return songs

    @staticmethod
    def sort(order, unordered):
        queued_songs = []
        for song in unordered:
            queued_songs.insert(order.index(song.id), song)
        return queued_songs


class SongrequestHistory(Base):
    __tablename__ = "songrequest_history"

    id = Column(INT, primary_key=True)
    stream_id = Column(INT, nullable=True)
    video_id = Column(TEXT, ForeignKey("songrequest_song_info.video_id"), nullable=False)
    date_finished = Column(UtcDateTime(), nullable=False)
    requested_by_id = Column(INT, ForeignKey("user.id"), nullable=True)
    skipped_by_id = Column(INT, ForeignKey("user.id"), nullable=True)
    skip_after = Column(INT, nullable=True)
    song_info = relationship("SongRequestSongInfo", foreign_keys=[video_id], lazy="joined")
    requested_by = relationship("User", foreign_keys=[requested_by_id], lazy="joined")
    skipped_by = relationship("User", foreign_keys=[skipped_by_id], lazy="joined")

    def jsonify(self):
        return {
            "id": self.id,
            "stream_id": self.stream_id,
            "video_id": self.video_id,
            "date_finished": str(self.date_finished),
            "requested_by": self.requested_by.username_raw if self.requested_by_id else None,
            "skipped_by": self.skipped_by.username_raw if self.skipped_by_id else None,
            "skip_after": self.skip_after,
        }

    def webjsonify(self):
        return {
            "song_info": self.song_info.jsonify(),
            "requested_by": self.requested_by.username_raw if self.requested_by_id else "Backup Playlist",
            "skipped_by": self.skipped_by.username_raw if self.skipped_by_id else None,
            "database_id": self.id,
            "date_finished": str(self.date_finished),
            "skip_after": self.skip_after,
            "formatted_duration": self.formatted_duration,
        }

    @property
    def formatted_duration(self):
        m, s = divmod(self.duration, 60)
        m = int(m)
        s = int(s)
        return f"{m:02d}:{s:02d}"

    @hybrid_property
    def link(self):
        return f"youtu.be/{self.video_id}"

    @hybrid_property
    def duration(self):
        return self.skip_after if self.skip_after else self.song_info.duration

    def requeue(self, db_session, requested_by):
        return SongrequestQueue.create(db_session, self.video_id, self.skip_after, requested_by)

    @staticmethod
    def create(db_session, stream_id, video_id, requested_by_id, skipped_by_id, skip_after):
        songrequesthistory = SongrequestHistory(
            stream_id=stream_id,
            video_id=video_id,
            date_finished=utils.now(),
            requested_by_id=requested_by_id,
            skipped_by_id=skipped_by_id,
            skip_after=skip_after,
        )
        db_session.add(songrequesthistory)
        return songrequesthistory

    @staticmethod
    def get_previous(db_session, position):
        songs = (
            db_session.query(SongrequestHistory)
            .populate_existing()
            .order_by(SongrequestHistory.id.desc())
            .limit(position + 1)
            .all()
        )
        if len(songs) == position + 1:
            return songs[position]

    @staticmethod
    def insert_previous(db_session, requested_by_id, position=0):
        previous = SongrequestHistory.get_previous(db_session, position)
        if not previous:
            return False
        return SongrequestQueue.create(db_session, previous.video_id, previous.skip_after, requested_by_id, 0)

    @staticmethod
    def get_list(db_session, size):
        return (
            db_session.query(SongrequestHistory)
            .populate_existing()
            .order_by(SongrequestHistory.id.desc())
            .limit(size)
            .all()
        )

    @staticmethod
    def from_id(db_session, _id):
        return db_session.query(SongrequestHistory).populate_existing().filter_by(id=_id).one_or_none()

    @staticmethod
    def get_history(db_session, limit):
        played_songs = (
            db_session.query(SongrequestHistory)
            .populate_existing()
            .filter(SongrequestHistory.song_info.has(banned=False))
            .order_by(SongrequestHistory.id.desc())
            .limit(limit)
            .all()
        )
        songs = []
        for song in played_songs:
            songs.append(song.webjsonify())
        return songs


class SongRequestSongInfo(Base):
    __tablename__ = "songrequest_song_info"

    video_id = Column(TEXT, primary_key=True, autoincrement=False)
    title = Column(TEXT, nullable=False)
    duration = Column(INT, nullable=False)
    default_thumbnail = Column(TEXT, nullable=False)
    banned = Column(BOOLEAN, default=False)
    favourite = Column(BOOLEAN, default=False)

    def jsonify(self):
        return {
            "video_id": self.video_id,
            "title": self.title,
            "duration": self.duration,
            "default_thumbnail": self.default_thumbnail,
            "banned": self.banned,
            "favourite": self.favourite,
            "formatted_duration": self.formatted_duration,
        }

    @property
    def formatted_duration(self):
        m, s = divmod(self.duration, 60)
        m = int(m)
        s = int(s)
        return f"{m:02d}:{s:02d}"

    @staticmethod
    def create(db_session, video_id, title, duration, default_thumbnail):
        songinfo = SongRequestSongInfo(
            video_id=video_id, title=title, duration=duration, default_thumbnail=default_thumbnail
        )
        db_session.add(songinfo)
        return songinfo

    @staticmethod
    def create_or_get(db_session, video_id, youtube):
        song_info = db_session.query(SongRequestSongInfo).populate_existing().filter_by(video_id=video_id).one_or_none()
        if song_info:
            return song_info

        import isodate

        if youtube is None:
            log.warning("youtube was not initialized")
            return False

        try:
            video_response = youtube.videos().list(id=str(video_id), part="snippet,contentDetails").execute()
        except:
            return False

        if not video_response.get("items", []):
            log.warning(f"Got no valid responses for {video_id}")
            return False

        video = video_response["items"][0]

        title = video["snippet"]["title"]
        duration = int(isodate.parse_duration(video["contentDetails"]["duration"]).total_seconds())
        default_thumbnail = video["snippet"]["thumbnails"]["default"]["url"]

        return SongRequestSongInfo.create(db_session, video_id, title, duration, default_thumbnail)

    @staticmethod
    def get(db_session, video_id):
        return db_session.query(SongRequestSongInfo).populate_existing().filter_by(video_id=video_id).one_or_none()

    @staticmethod
    def get_banned(db_session):
        return (
            db_session.query(SongRequestSongInfo)
            .populate_existing()
            .filter_by(banned=True)
            .order_by(SongRequestSongInfo.video_id)
            .all()
        )

    @staticmethod
    def get_favourite(db_session):
        return (
            db_session.query(SongRequestSongInfo)
            .populate_existing()
            .filter_by(favourite=True)
            .order_by(SongRequestSongInfo.video_id)
            .all()
        )
