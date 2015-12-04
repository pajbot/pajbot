from tyggbot.models.user import User
from tyggbot.models.pleblist import PleblistSong
from tyggbot.models.stream import Stream
from tyggbot.models.db import DBManager

from flask import Blueprint
from flask import jsonify
from flask import make_response
from flask import request
from sqlalchemy import func


page = Blueprint('api', __name__)

sqlconn = False


@page.route('/api/v1/user/<username>')
def get_user(username):
    session = DBManager.create_session()
    user = session.query(User).filter_by(username=username).one_or_none()
    if user is None:
        return make_response(jsonify({'error': 'Not found'}), 404)

    rank = session.query(func.Count(User.id)).filter(User.points > user.points).one()
    rank = rank[0] + 1
    session.close()
    if user:
        accessible_data = {
                'id': user.id,
                'username': user.username,
                'username_raw': user.username_raw,
                'points': user.points,
                'rank': rank,
                'level': user.level,
                'last_seen': user.last_seen,
                'last_active': user.last_active,
                'subscriber': user.subscriber,
                'num_lines': user.num_lines,
                'minutes_in_chat_online': user.minutes_in_chat_online,
                'minutes_in_chat_offline': user.minutes_in_chat_offline,
                'banned': user.banned,
                'ignored': user.ignored,
                }
        return jsonify(accessible_data)

    return make_response(jsonify({'error': 'Not found'}), 404)


@page.route('/api/v1/pleblist/list')
def pleblist_list():
    with DBManager.create_session_scope() as session:
        current_stream = session.query(Stream).filter_by(ended=False).order_by(Stream.stream_start).first()
        if current_stream is None:
            return make_response(jsonify({'error': 'Stream offline'}), 404)

        songs = session.query(PleblistSong).filter_by(stream_id=current_stream.id).all()

        payload = {
                '_total': len(songs),
                'songs': songs,
                }

        return jsonify(payload)


@page.route('/api/v1/pleblist/list/<stream_id>')
def pleblist_list_by_stream(stream_id):
    with DBManager.create_session_scope() as session:
        songs = session.query(PleblistSong).filter_by(stream_id=stream_id).all()

        payload = {
                '_total': len(songs),
                'songs': songs,
                }

        return jsonify(payload)


@page.route('/api/v1/pleblist/add')
def pleblist_add():
    if not request.method == 'POST':
        return make_response(jsonify({'error': 'Invalid request method'}))
    if 'youtube_id' not in request.form:
        return make_response(jsonify({'error': 'Missing data youtube_id'}))
    with DBManager.create_session_scope() as session:
        youtube_id = request.form['youtube_id']
        current_stream = session.query(Stream).filter_by(ended=False).order_by(Stream.stream_start).first()
        if current_stream is None:
            return make_response(jsonify({'error': 'Stream offline'}), 404)

        song_requested = PleblistSong(current_stream.id, youtube_id)
        session.add(song_requested)

        return jsonify({'success': True})


@page.route('/api/v1/pleblist/next')
def pleblist_next():
    with DBManager.create_session_scope() as session:
        current_stream = session.query(Stream).filter_by(ended=False).order_by(Stream.stream_start).first()
        if current_stream is None:
            return make_response(jsonify({'error': 'Stream offline'}), 404)

        # TODO: implement this

        return make_response(jsonify({'error': 'NOT IMPLEMENTED'}), 400)

        # return jsonify({'success': True})


@page.route('/api/v1/pleblist/blacklist')
def pleblist_blacklist():
    with DBManager.create_session_scope() as session:
        current_stream = session.query(Stream).filter_by(ended=False).order_by(Stream.stream_start).first()
        if current_stream is None:
            return make_response(jsonify({'error': 'Stream offline'}), 404)

        # TODO: implement this

        return make_response(jsonify({'error': 'NOT IMPLEMENTED'}), 400)

        # return jsonify({'success': True})
