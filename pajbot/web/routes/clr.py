import datetime
import base64
import binascii
import logging
import socket
import json
import time

from pajbot.web.utils import requires_level
from pajbot.web.utils import nocache
from pajbot.models.user import User
from pajbot.models.emote import Emote
from pajbot.models.stream import Stream
from pajbot.models.db import DBManager
from pajbot.models.sock import SocketClientManager
from pajbot.managers.redis import RedisManager
from pajbot.streamhelper import StreamHelper

from flask import Blueprint
from flask import render_template
from flask import abort

page = Blueprint('clr', __name__, url_prefix='/clr')
config = None

log = logging.getLogger('pajbot')

@page.route('/overlay/<widget_id>')
@nocache
def overlay(widget_id):
    return render_template('clr/overlay.html',
            widget={})

@page.route('/donations/<widget_id>')
@nocache
def donations(widget_id):
    redis = RedisManager.get()
    widget = redis.hget(
            '{streamer}:clr:donations'.format(streamer=StreamHelper.get_streamer()),
            widget_id)
    if widget is None:
        abort(404)

    tts_authentication = ''
    if 'extra' in config:
        tts_authentication = config['extra'].get('tts_authentication', '')

    with DBManager.create_session_scope() as db_session:
        emotes = db_session.query(Emote).all()
        return render_template('clr/donations.html',
                widget=json.loads(widget),
                emotes=emotes,
                tts_authentication=tts_authentication)
