import json
import logging

from flask import abort
from flask import Blueprint
from flask import render_template

from pajbot.managers.redis import RedisManager
from pajbot.streamhelper import StreamHelper
from pajbot.web.utils import nocache

page = Blueprint('clr', __name__, url_prefix='/clr')
config = None

log = logging.getLogger('pajbot')


@page.route('/overlay/<widget_id>')
@page.route('/overlay/<widget_id>/<random_shit>')
@nocache
def overlay(widget_id, **options):
    return render_template('clr/overlay.html',
            widget={})


@page.route('/fatoverlay/<widget_id>')
@page.route('/fatoverlay/<widget_id>/<random_shit>')
@nocache
def fatoverlay(widget_id, **options):
    return render_template('clr/fatoverlay.html',
            widget={})


@page.route('/crazyoverlay/<widget_id>')
@page.route('/crazyoverlay/<widget_id>/<random_shit>')
@nocache
def crazyoverlay(widget_id, **options):
    return render_template('clr/crazyoverlay.html',
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

    widget = json.loads(widget)

    # Assign indices to all styles and conditions
    i = 0
    log.info(widget['styles'])
    for style in widget['styles']:
        style['index'] = i
        i += 1
    log.info(widget['styles'])
    i = 0
    j = 0
    for condition in widget['conditions']:
        condition['index'] = i
        i += 1
        for style in condition['styles']:
            style['index'] = j
            j += 1
    log.info(widget)

    operator_order = {
            '==': 100,
            '>=': 50,
            '<=': 50,
            }

    widget['conditions'].sort(key=lambda c: (operator_order[c['operator']], c['amount']))

    tts_authentication = ''
    tts_endpoint = ''
    if 'extra' in config:
        tts_authentication = config['extra'].get('tts_authentication', '')
        tts_endpoint = config['extra'].get('tts_endpoint', '')

    redis = RedisManager.get()
    twitch_emotes = redis.hgetall('global:emotes:twitch')
    bttv_emotes = redis.hgetall('global:emotes:bttv')
    emotes = []
    for emote in twitch_emotes:
        emotes.append({
            'code': emote,
            'emote_id': twitch_emotes[emote],
            })
    for emote in bttv_emotes:
        emotes.append({
            'code': emote,
            'emote_hash': bttv_emotes[emote],
            })
    emotes.sort(key=lambda emote: len(emote['code']), reverse=True)
    return render_template('clr/donations.html',
            widget=widget,
            emotes=emotes,
            tts_authentication=tts_authentication,
            tts_endpoint=tts_endpoint)
