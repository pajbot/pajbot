import logging

from flask import redirect
from flask import render_template

from pajbot.managers.db import DBManager
from pajbot.models.pleblist import PleblistSong
from pajbot.models.stream import Stream
from pajbot.models.stream import StreamChunk
from pajbot.models.user import User
from pajbot.utils import find

log = logging.getLogger(__name__)


def init(app):
    @app.route('/pleblist/')
    def pleblist():
        return render_template('pleblist.html')

    @app.route('/pleblist/host/')
    def pleblist_host():
        return render_template('pleblist_host.html')

    @app.route('/pleblist/history/')
    def pleblist_history_redirect():
        with DBManager.create_session_scope() as session:
            current_stream = session.query(Stream).filter_by(ended=False).order_by(Stream.stream_start.desc()).first()
            if current_stream is not None:
                return redirect('/pleblist/history/{}/'.format(current_stream.id), 303)

            last_stream = session.query(Stream).filter_by(ended=True).order_by(Stream.stream_start.desc()).first()
            if last_stream is not None:
                return redirect('/pleblist/history/{}/'.format(last_stream.id), 303)

            return render_template('pleblist_history_no_stream.html'), 404

    @app.route('/pleblist/history/<int:stream_id>/')
    def pleblist_history_stream(stream_id):
        with DBManager.create_session_scope() as session:
            stream = session.query(Stream).filter_by(id=stream_id).one_or_none()
            if stream is None:
                return render_template('pleblist_history_404.html'), 404

            previous_stream = session.query(Stream).filter_by(id=stream_id - 1).one_or_none()
            next_stream = session.query(Stream).filter_by(id=stream_id + 1).one_or_none()

            q = session.query(PleblistSong, User).outerjoin(User, PleblistSong.user_id == User.id).filter(PleblistSong.stream_id == stream.id).order_by(PleblistSong.id.asc(), PleblistSong.id.asc())
            songs = []
            for song, user in q:
                song.user = user
                songs.append(song)

            total_length_left = sum([song.skip_after or song.song_info.duration if song.date_played is None and song.song_info is not None else 0 for song in songs])

            first_unplayed_song = find(lambda song: song.date_played is None, songs)
            stream_chunks = session.query(StreamChunk).filter(StreamChunk.stream_id == stream.id).all()

            return render_template('pleblist_history.html',
                    stream=stream,
                    previous_stream=previous_stream,
                    next_stream=next_stream,
                    songs=songs,
                    total_length_left=total_length_left,
                    first_unplayed_song=first_unplayed_song,
                    stream_chunks=stream_chunks)
