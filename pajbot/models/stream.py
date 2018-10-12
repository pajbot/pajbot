import argparse
import collections
import datetime
import json
import logging
import math
import urllib

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import reconstructor
from sqlalchemy.orm import relationship

from pajbot.managers.db import Base
from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.managers.redis import RedisManager

log = logging.getLogger('pajbot')


def parse_twitch_datetime(datetime_str):
    return datetime.datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%SZ')


class Stream(Base):
    __tablename__ = 'tb_stream'

    id = Column(Integer, primary_key=True)
    title = Column(String(256), nullable=False)
    stream_start = Column(DateTime, nullable=False)
    stream_end = Column(DateTime, nullable=True)
    ended = Column(Boolean, nullable=False, default=False)

    stream_chunks = relationship('StreamChunk',
            backref='stream',
            cascade='save-update, merge, expunge',
            lazy='joined')

    def __init__(self, created_at, **options):
        self.id = None
        self.title = options.get('title', 'NO TITLE')
        self.stream_start = parse_twitch_datetime(created_at)
        self.stream_end = None
        self.ended = False

    @property
    def uptime(self):
        """
        Returns a TimeDelta for how long the stream was online, or is online.
        """

        if self.ended is False:
            return datetime.datetime.now() - self.stream_start
        else:
            return self.stream_end - self.stream_start


class StreamChunk(Base):
    __tablename__ = 'tb_stream_chunk'

    id = Column(Integer, primary_key=True)
    stream_id = Column(Integer, ForeignKey('tb_stream.id'), nullable=False)
    broadcast_id = Column(BIGINT(unsigned=True), nullable=False)
    video_url = Column(String(128), nullable=True)
    video_preview_image_url = Column(String(256), nullable=True)
    chunk_start = Column(DateTime, nullable=False)
    chunk_end = Column(DateTime, nullable=True)

    highlights = relationship('StreamChunkHighlight',
            backref='stream_chunk',
            cascade='save-update, merge, expunge',
            lazy='joined')

    def __init__(self, stream, broadcast_id, created_at, **options):
        self.id = None
        self.stream_id = stream.id
        self.broadcast_id = broadcast_id
        self.video_url = None
        self.video_preview_image_url = None
        self.chunk_start = parse_twitch_datetime(created_at)
        self.chunk_end = None

        self.stream = stream

        self.highlights = []


class StreamChunkHighlight(Base):
    __tablename__ = 'tb_stream_chunk_highlight'

    id = Column(Integer, primary_key=True)
    stream_chunk_id = Column(Integer, ForeignKey('tb_stream_chunk.id'), nullable=False)
    created_by = Column(Integer, nullable=True)
    last_edited_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False)
    highlight_offset = Column(Integer, nullable=False)
    description = Column(String(128), nullable=True)
    override_link = Column(String(256), nullable=True)
    thumbnail = Column(Boolean, nullable=True, default=None)
    video_url = None

    created_by_user = relationship('User',
            lazy='noload',
            primaryjoin='User.id==StreamChunkHighlight.created_by',
            foreign_keys='StreamChunkHighlight.created_by',
            cascade='save-update, merge, expunge',
            uselist=False)
    last_edited_by_user = relationship('User',
            lazy='noload',
            primaryjoin='User.id==StreamChunkHighlight.last_edited_by',
            foreign_keys='StreamChunkHighlight.last_edited_by',
            cascade='save-update, merge, expunge',
            uselist=False)

    DEFAULT_OFFSET = 0

    def __init__(self, stream_chunk, **options):
        self.stream_chunk_id = stream_chunk.id
        self.created_at = datetime.datetime.now()
        self.highlight_offset = options.get('offset', self.DEFAULT_OFFSET)
        self.description = options.get('description', None)
        self.override_link = options.get('override_link', None)
        self.thumbnail = None
        self.created_by = options.get('created_by', None)
        self.last_edited_by = options.get('last_edited_by', None)

        self.stream_chunk = stream_chunk
        self.refresh_video_url()

        stream_chunk.highlights.append(self)

    @reconstructor
    def on_load(self):
        self.refresh_video_url()

    @hybrid_property
    def created_at_with_offset(self):
        return self.created_at - self.highlight_offset

    def refresh_video_url(self):
        if self.override_link is not None:
            self.video_url = self.override_link
        elif self.stream_chunk.video_url is None:
            self.video_url = None
        else:
            date_diff = self.created_at - self.stream_chunk.chunk_start
            total_seconds = date_diff.total_seconds()
            total_seconds -= abs(self.highlight_offset)
            timedata = collections.OrderedDict()
            timedata['h'] = math.trunc(total_seconds / 3600)
            timedata['m'] = math.trunc(total_seconds / 60 % 60)
            timedata['s'] = math.trunc(total_seconds % 60)
            pretimedata = {
                    'h': 0,
                    'm': timedata['h'],
                    's': timedata['h'] + timedata['m']
                    }
            # XXX: Is it an issue if the format is like this: ?t=03m
            # i.e. a time format with minutes but _not_ seconds? try it out
            timestamp = ''.join(['{value:02d}{key}'.format(value=value, key=key) for key, value in timedata.items() if value > 0 or pretimedata[key] > 0])
            self.video_url = '{stream_chunk.video_url}?t={timestamp}'.format(stream_chunk=self.stream_chunk, timestamp=timestamp)


class StreamManager:
    NUM_OFFLINES_REQUIRED = 10
    STATUS_CHECK_INTERVAL = 20  # seconds
    VIDEO_URL_CHECK_INTERVAL = 60 * 5  # seconds

    def fetch_video_url_stage1(self):
        if self.online is False:
            return

        try:
            data = self.bot.twitchapi.get(['channels', self.bot.streamer, 'videos'], parameters={'broadcasts': 'true'}, base='https://api.twitch.tv/kraken/')

            self.bot.mainthread_queue.add(self.refresh_video_url_stage2,
                    args=[data])
        except urllib.error.HTTPError as e:
            raw_data = e.read().decode('utf-8')
            log.exception('OMGScoots')
            log.info(raw_data)
        except:
            log.exception('Uncaught exception in fetch_video_url')

    def fetch_video_url_stage2(self, data):
        stream_chunk = self.current_stream_chunk if self.current_stream_chunk.video_url is None else None
        try:
            for video in data['videos']:
                if video['broadcast_type'] == 'archive':
                    recorded_at = parse_twitch_datetime(video['recorded_at'])
                    if stream_chunk is not None:
                        time_diff = stream_chunk.chunk_start - recorded_at
                        if abs(time_diff.total_seconds()) < 60 * 5:
                            # we found the relevant video!
                            return video['url'], video['preview'], video['recorded_at']
                    else:
                        if video['status'] == 'recording':
                            return video['url'], video['preview'], video['recorded_at']
        except urllib.error.HTTPError as e:
            raw_data = e.read().decode('utf-8')
            log.exception('OMGScoots')
            log.info(raw_data)
        except:
            log.exception('Uncaught exception in fetch_video_url')

        return None, None, None

    def __init__(self, bot):
        self.bot = bot

        self.current_stream_chunk = None  # should this even exist?

        self.num_offlines = 0
        self.first_offline = None

        self.num_viewers = 0

        self.game = 'Loading...'
        self.title = 'Loading...'

        self.bot.execute_every(self.STATUS_CHECK_INTERVAL,
                self.bot.action_queue.add,
                (self.refresh_stream_status_stage1, ))
        self.bot.execute_every(self.VIDEO_URL_CHECK_INTERVAL,
                self.bot.action_queue.add,
                (self.refresh_video_url_stage1, ))

        """
        This will load the latest stream so we can post an accurate
        "time since last online" figure.
        """
        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            self.current_stream = db_session.query(Stream).filter_by(ended=False).order_by(Stream.stream_start.desc()).first()
            self.last_stream = db_session.query(Stream).filter_by(ended=True).order_by(Stream.stream_end.desc()).first()
            if self.current_stream:
                self.current_stream_chunk = db_session.query(StreamChunk).filter_by(stream_id=self.current_stream.id).order_by(StreamChunk.chunk_start.desc()).first()
                log.info('Set current stream chunk here to {0}'.format(self.current_stream_chunk))
            db_session.expunge_all()

    def get_viewer_data(self, redis=None):
        if self.offline:
            return False

        if not redis:
            redis = RedisManager.get()

        data = redis.hget(
                '{streamer}:viewer_data'.format(streamer=self.bot.streamer),
                self.current_stream.id)

        if data is None:
            data = {}
        else:
            data = json.loads(data)

        return data

    def update_chatters(self, chatters, minutes):
        """
        chatters is a list of usernames
        """

        if self.offline:
            return False

        redis = RedisManager.get()

        data = self.get_viewer_data(redis=redis)

        for chatter in chatters:
            if chatter in data:
                data[chatter] += minutes
            else:
                data[chatter] = minutes

        redis.hset(
                '{streamer}:viewer_data'.format(streamer=self.bot.streamer),
                self.current_stream.id,
                json.dumps(data, separators=(',', ':')))

    @property
    def online(self):
        return self.current_stream is not None

    @property
    def offline(self):
        return self.current_stream is None

    def commit(self):
        log.info('commiting something?')

    def create_stream_chunk(self, status):
        if self.current_stream_chunk is not None:
            # There's already a stream chunk started!
            self.current_stream_chunk.chunk_end = datetime.datetime.now()
            DBManager.session_add_expunge(self.current_stream_chunk)

        stream_chunk = None

        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            stream_chunk = db_session.query(StreamChunk).filter_by(broadcast_id=status['broadcast_id']).one_or_none()
            if stream_chunk is None:
                log.info('Creating stream chunk, from create_stream_chunk')
                stream_chunk = StreamChunk(self.current_stream, status['broadcast_id'], status['created_at'])
                self.current_stream_chunk = stream_chunk
                db_session.add(stream_chunk)
                db_session.commit()
            else:
                log.info('We already have a stream chunk!')
                self.current_stream_chunk = stream_chunk
                stream_chunk = None
            db_session.expunge_all()

        if stream_chunk:
            self.current_stream.stream_chunks.append(stream_chunk)

    def create_stream(self, status):
        log.info('Attempting to create a stream!')
        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            stream_chunk = db_session.query(StreamChunk).filter_by(broadcast_id=status['broadcast_id']).one_or_none()
            new_stream = False
            if stream_chunk is not None:
                stream = stream_chunk.stream
            else:
                log.info('checking if there is an active stream already')
                stream = db_session.query(Stream).filter_by(ended=False).order_by(Stream.stream_start.desc()).first()
                new_stream = stream is None

                if new_stream:
                    log.info('No active stream, create new!')
                    stream = Stream(status['created_at'],
                            title=status['title'])
                    db_session.add(stream)
                    db_session.commit()
                    log.info('Successfully added stream!')
                stream_chunk = StreamChunk(stream, status['broadcast_id'], status['created_at'])
                db_session.add(stream_chunk)
                db_session.commit()
                stream.stream_chunks.append(stream_chunk)
                log.info('Created stream chunk')

            self.current_stream = stream
            self.current_stream_chunk = stream_chunk
            db_session.expunge_all()

            if new_stream:
                HandlerManager.trigger('on_stream_start', stop_on_false=False)

            log.info('Successfully created a stream')

    def go_offline(self):
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

        HandlerManager.trigger('on_stream_stop', stop_on_false=False)

    def refresh_stream_status_stage1(self):
        try:
            status = self.bot.twitchapi.get_status(self.bot.streamer)
            if status['error'] is True:
                # log.error('An error occured while fetching stream status')
                # I'll comment this out since all errors are posted live anyway
                return

            self.bot.mainthread_queue.add(self.refresh_stream_status_stage2,
                    args=[status])
        except:
            log.exception('Uncaught exception while refreshing stream status (Stage 1)')

    def refresh_stream_status_stage2(self, status):
        try:
            redis = RedisManager.get()

            redis.hmset('stream_data', {
                '{streamer}:online'.format(streamer=self.bot.streamer): status['online'],
                '{streamer}:viewers'.format(streamer=self.bot.streamer): status['viewers'],
                '{streamer}:game'.format(streamer=self.bot.streamer): status['game'],
                })

            self.num_viewers = status['viewers']
            self.game = status['game']
            self.title = status['title']

            if status['online']:
                if self.current_stream is None:
                    self.create_stream(status)
                if self.current_stream_chunk is None:
                    self.create_stream_chunk(status)
                if self.current_stream_chunk.broadcast_id != status['broadcast_id']:
                    log.debug('Detected a new chunk!')
                    self.create_stream_chunk(status)

                self.num_offlines = 0
                self.first_offline = None
            else:
                if self.online is True:
                    log.info('Offline. {0}'.format(self.num_offlines))
                    if self.first_offline is None:
                        self.first_offline = datetime.datetime.now()

                    if self.num_offlines >= 10:
                        log.info('Switching to offline state!')
                        self.go_offline()
                    self.num_offlines += 1
        except:
            log.exception('Uncaught exception while refreshing stream status (Stage 2)')

    def refresh_video_url_stage1(self):
        self.fetch_video_url_stage1()

    def refresh_video_url_stage2(self, data):
        if self.online is False:
            return

        if self.current_stream_chunk is None or self.current_stream is None:
            return

        log.info('Attempting to fetch video url for broadcast {0}'.format(self.current_stream_chunk.broadcast_id))
        stream_chunk = self.current_stream_chunk if self.current_stream_chunk.video_url is None else None
        video_url, video_preview_image_url, video_recorded_at = self.fetch_video_url_stage2(data)
        if video_url is not None:
            log.info('Successfully fetched a video url: {0}'.format(video_url))
            if self.current_stream_chunk is None or self.current_stream_chunk.video_url is None:
                with DBManager.create_session_scope(expire_on_commit=False) as db_session:
                    self.current_stream_chunk.video_url = video_url
                    self.current_stream_chunk.video_preview_image_url = video_preview_image_url

                    db_session.add(self.current_stream_chunk)

                    db_session.commit()

                    db_session.expunge_all()
                log.info('Successfully commited video url data.')
            elif self.current_stream_chunk.video_url != video_url:
                # End current stream chunk
                self.current_stream_chunk.chunk_end = datetime.datetime.now()
                DBManager.session_add_expunge(self.current_stream_chunk)

                with DBManager.create_session_scope(expire_on_commit=False) as db_session:
                    stream_chunk = StreamChunk(self.current_stream, self.current_stream_chunk.broadcast_id, video_recorded_at)
                    self.current_stream_chunk = stream_chunk
                    self.current_stream_chunk.video_url = video_url
                    self.current_stream_chunk.video_preview_image_url = video_preview_image_url

                    db_session.add(self.current_stream_chunk)

                    db_session.commit()

                    db_session.expunge_all()
                log.info('Successfully commited video url data in a new chunk.')
        else:
            log.info('Not video for broadcast found')

    def create_highlight(self, **options):
        """
        Returns an error message (string) if something went wrong, otherwise returns True
        """
        if self.online is False or self.current_stream_chunk is None:
            return 'The stream is not online'

        if self.current_stream_chunk.video_url is None:
            return 'No video URL fetched for this chunk yet, try in 5 minutes'

        try:
            highlight = StreamChunkHighlight(self.current_stream_chunk, **options)

            with DBManager.create_session_scope(expire_on_commit=False) as db_session:
                db_session.add(highlight)
                db_session.add(self.current_stream_chunk)
        except:
            log.exception('uncaught exception in create_highlight')
            return 'Unknown reason, ask pajlada'

        return True

    def parse_highlight_arguments(self, message):
        parser = argparse.ArgumentParser()
        parser.add_argument('--offset', dest='offset', type=int)
        parser.add_argument('--id', dest='id', type=int)
        parser.add_argument('--link', dest='override_link')
        parser.add_argument('--url', dest='override_link')
        parser.add_argument('--overridelink', dest='override_link')
        parser.add_argument('--no-link', dest='override_link', action='store_false')

        try:
            args, unknown = parser.parse_known_args(message.split())
        except SystemExit:
            return False, False
        except:
            log.exception('Unhandled exception in add_highlight')
            return False, False

        # Strip options of any values that are set as None
        options = {k: v for k, v in vars(args).items() if v is not None}
        response = ' '.join(unknown)

        if 'override_link' in options and options['override_link'] is False:
            options['override_link'] = None

        return options, response

    def update_highlight(self, id, **options):
        """
        Returns True if a highlight was modified, otherwise return False
        """

        if 'offset' in options:
            options['highlight_offset'] = options.pop('offset')

        num_rows = 0
        try:
            with DBManager.create_session_scope() as db_session:
                num_rows = db_session.query(StreamChunkHighlight).filter_by(id=id).update(options)
        except:
            log.exception('AAAAAAAAAA FIXME')

        return (num_rows == 1)

    def remove_highlight(self, id):
        """
        Returns True if a highlight was removed, otherwise return False
        """

        with DBManager.create_session_scope() as db_session:
            num_rows = db_session.query(StreamChunkHighlight).filter(StreamChunkHighlight.id == id).delete()

        return (num_rows == 1)

    def get_stream_value(self, key, extra={}):
        return getattr(self, key, None)

    def get_current_stream_value(self, key, extra={}):
        if self.current_stream is not None:
            return getattr(self.current_stream, key, None)
        else:
            return None

    def get_last_stream_value(self, key, extra={}):
        if self.last_stream is not None:
            return getattr(self.last_stream, key, None)
        else:
            return None
