import datetime
import base64
import binascii
import logging

from tyggbot.web.utils import requires_level
from tyggbot.models.user import User
from tyggbot.models.pleblist import PleblistSong
from tyggbot.models.pleblist import PleblistSongInfo
from tyggbot.models.pleblist import PleblistManager
from tyggbot.models.stream import Stream
from tyggbot.models.db import DBManager

import requests
from flask import Blueprint
from flask import jsonify
from flask import make_response
from flask import request
from flask import redirect
from flask.ext.scrypt import generate_password_hash
from flask.ext.scrypt import check_password_hash
from sqlalchemy import func
from sqlalchemy import and_


from functools import wraps, update_wrapper


page = Blueprint('api', __name__)
config = None

sqlconn = False

log = logging.getLogger('tyggbot')


def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Last-Modified'] = datetime.datetime.now()
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    return update_wrapper(no_cache, view)


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
            return make_response(jsonify({'error': 'Stream offline'}), 400)

        songs = session.query(PleblistSong).filter(PleblistSong.stream_id == current_stream.id, PleblistSong.date_played.is_(None)).all()
        payload = {
                '_total': len(songs),
                'songs': [song.jsonify() for song in songs],
                }

        return jsonify(payload)

@page.route('/api/v1/pleblist/list/after/<song_id>')
@nocache
def pleblist_list_after(song_id):
    with DBManager.create_session_scope() as session:
        current_stream = session.query(Stream).filter_by(ended=False).order_by(Stream.stream_start).first()
        if current_stream is None:
            return make_response(jsonify({'error': 'Stream offline'}), 400)

        songs = session.query(PleblistSong).filter(and_(PleblistSong.stream_id == current_stream.id, PleblistSong.date_played.is_(None), PleblistSong.id > song_id)).all()

        payload = {
                '_total': len(songs),
                'songs': [song.jsonify() for song in songs],
                }

        return jsonify(payload)


@page.route('/api/v1/pleblist/list/<stream_id>')
def pleblist_list_by_stream(stream_id):
    with DBManager.create_session_scope() as session:
        songs = session.query(PleblistSong).filter_by(stream_id=stream_id).all()

        payload = {
                '_total': len(songs),
                'songs': [song.jsonify() for song in songs],
                }

        return jsonify(payload)


@page.route('/api/v1/pleblist/add', methods=['POST', 'GET'])
def pleblist_add():
    if not request.method == 'POST':
        return make_response(jsonify({'error': 'Invalid request method'}), 405)
    if 'youtube_id' not in request.form:
        return make_response(jsonify({'error': 'Missing data youtube_id'}), 400)
    if 'password' not in request.form:
        return make_response(jsonify({'error': 'Missing data password'}), 400)
    salted_password = generate_password_hash(config['web']['pleblist_password'], config['web']['pleblist_password_salt'])
    try:
        user_password = base64.b64decode(request.form['password'])
    except binascii.Error:
        return make_response(jsonify({'error': 'Invalid data password'}), 400)
    if not user_password == salted_password:
        return make_response(jsonify({'error': 'Invalid password'}), 401)

    with DBManager.create_session_scope() as session:
        youtube_id = request.form['youtube_id']
        current_stream = session.query(Stream).filter_by(ended=False).order_by(Stream.stream_start).first()
        if current_stream is None:
            return make_response(jsonify({'error': 'Stream offline'}), 400)

        song_requested = PleblistSong(current_stream.id, youtube_id)
        session.add(song_requested)
        song_info = session.query(PleblistSongInfo).filter_by(pleblist_song_youtube_id=youtube_id).first()
        if song_info is None and song_requested.song_info is None:
            PleblistManager.init(config['youtube']['developer_key'])
            song_info = PleblistManager.create_pleblist_song_info(song_requested.youtube_id)
            if song_info is not False:
                session.add(song_info)
                session.commit()

        return jsonify({'success': True})


@page.route('/api/v1/pleblist/next', methods=['POST', 'GET'])
def pleblist_next():
    if not request.method == 'POST':
        return make_response(jsonify({'error': 'Invalid request method'}), 405)
    if 'song_id' not in request.form:
        return make_response(jsonify({'error': 'Missing data song_id'}), 400)
    if 'password' not in request.form:
        return make_response(jsonify({'error': 'Missing data password'}), 400)
    salted_password = generate_password_hash(config['web']['pleblist_password'], config['web']['pleblist_password_salt'])
    try:
        user_password = base64.b64decode(request.form['password'])
    except binascii.Error:
        return make_response(jsonify({'error': 'Invalid data password'}), 400)
    if not user_password == salted_password:
        return make_response(jsonify({'error': 'Invalid password'}), 401)

    with DBManager.create_session_scope() as session:
        try:
            current_song = session.query(PleblistSong).filter(PleblistSong.id == int(request.form['song_id'])).order_by(PleblistSong.date_added.asc()).first()
        except ValueError:
            return make_response(jsonify({'error': 'Invalid data song_id'}), 400)

        if current_song is None:
            return make_response(jsonify({'error': 'No song active in the pleblist'}), 404)

        current_song.date_played = datetime.datetime.now()
        session.commit()

        # TODO: Add more data.
        # Was this song forcefully skipped? Or did it end naturally.

        return jsonify({'message': 'Success!'})


@page.route('/api/v1/pleblist/validate', methods=['POST', 'GET'])
def pleblist_validate():
    if not request.method == 'POST':
        return make_response(jsonify({'error': 'Invalid request method'}), 405)
    if 'youtube_id' not in request.form:
        return make_response(jsonify({'error': 'Missing data youtube_id'}), 400)

    with DBManager.create_session_scope() as session:
        youtube_id = request.form['youtube_id']
        print(youtube_id)
        song_info = session.query(PleblistSongInfo).filter_by(pleblist_song_youtube_id=youtube_id).first()
        if song_info is not None:
            return jsonify({
                'message': 'success',
                'song_info': song_info.jsonify()
                })

        PleblistManager.init(config['youtube']['developer_key'])
        song_info = PleblistManager.create_pleblist_song_info(youtube_id)
        if not song_info and len(youtube_id) > 11:
            youtube_id = youtube_id[:11]
            song_info = session.query(PleblistSongInfo).filter_by(pleblist_song_youtube_id=youtube_id).first()
            if song_info is not None:
                return jsonify({
                    'message': 'success',
                    'new_youtube_id': youtube_id,
                    'song_info': song_info.jsonify()
                    })
            else:
                song_info = PleblistManager.create_pleblist_song_info(youtube_id)

        if song_info:
            print(song_info)
            session.add(song_info)
            session.commit()
            return jsonify({
                'message': 'success',
                'new_youtube_id': youtube_id,
                'song_info': song_info.jsonify()
                })

        return jsonify({
            'message': 'invalid youtube id',
            'song_info': None
            })


@page.route('/api/v1/pleblist/blacklist')
def pleblist_blacklist():
    with DBManager.create_session_scope() as session:
        current_stream = session.query(Stream).filter_by(ended=False).order_by(Stream.stream_start).first()
        if current_stream is None:
            return make_response(jsonify({'error': 'Stream offline'}), 400)

        # TODO: implement this

        return make_response(jsonify({'error': 'NOT IMPLEMENTED'}), 400)

        # return jsonify({'success': True})


@page.route('/api/v1/streamtip/oauth')
def streamtip_oauth():
    if not request.method == 'GET':
        return make_response(jsonify({'error': 'Invalid request method. (Expected GET)'}), 400)

    if 'code' not in request.args:
        return make_response(jsonify({'error': 'Missing `code` parameter.'}), 400)

    if 'streamtip' not in config:
        return make_response(jsonify({'error': 'Config not set up properly.'}), 400)

    payload = {
            'client_id': config['streamtip']['client_id'],
            'client_secret': config['streamtip']['client_secret'],
            'grant_type': 'authorization_code',
            'redirect_uri': config['streamtip']['redirect_uri'],
            'code': request.args['code'],
            }

    r = requests.post('https://streamtip.com/api/oauth2/token', data=payload)

    return redirect('/pleblist/host/#{}'.format(r.json()['access_token']), 303)


@page.route('/api/v1/streamtip/validate', methods=['POST', 'GET'])
def streamtip_validate():
    if not request.method == 'POST':
        return make_response(jsonify({'error': 'Invalid request method. (Expected POST)'}), 400)

    if 'access_token' not in request.form:
        return make_response(jsonify({'error': 'Missing `access_token` parameter.'}), 400)

    if 'streamtip' not in config:
        return make_response(jsonify({'error': 'Config not set up properly.'}), 400)

    r = requests.get('https://streamtip.com/api/me?access_token={}'.format(request.form['access_token']))
    if r.json()['user']['_id'] == config['web']['pleblist_streamtip_userid']:
        salted_password = generate_password_hash(config['web']['pleblist_password'], config['web']['pleblist_password_salt'])
        password = base64.b64encode(salted_password)
        resp = make_response(jsonify({'password': password}))
        resp.set_cookie('password', password)
        return resp
    else:
        return make_response(jsonify({'error': 'Invalid user ID'}), 400)

@page.route('/api/v1/push/command/update/<command_id>')
def push_command_update(command_id):
    import socket
    import json

    payload = {
            'event': 'command.update',
            'data': {
                'command_id': command_id
                }
            }
    payload_bytes = json.dumps(payload).encode('utf-8')

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(config['sock']['sock_file'])
            client.sendall(payload_bytes)
            return make_response(jsonify({'success': 'good job'}))
    except:
        log.exception('???')
        return make_response(jsonify({'error': 'Could not push update'}))
