import json
import logging

from flask import abort
from flask import Blueprint
from flask import render_template

from pajbot.managers import DBManager
from pajbot.managers.redis import RedisManager
from pajbot.models.emote import Emote
from pajbot.streamhelper import StreamHelper
from pajbot.web.utils import nocache

page = Blueprint('clr', __name__, url_prefix='/clr')
config = None

log = logging.getLogger('pajbot')

@page.route('/overlay/<widget_id>')
@nocache
def overlay(widget_id):
    return render_template('clr/overlay.html',
            widget={})

@page.route('/donations/<widget_id>')
@page.route('/donations/<widget_id>/<random_shit>')
@nocache
def donations(widget_id, **options):
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
