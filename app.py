#!/usr/bin/env python3

import sys
import argparse
import os
import configparser
import json
import math
import logging
import subprocess
import datetime
import urllib
from PIL import Image

from tyggbot.tyggbot import TyggBot
from tyggbot.web.models import api
from tyggbot.web.routes import admin
from tyggbot.web.models import errors
from tyggbot.models.db import DBManager
from tyggbot.tbutil import load_config, init_logging, time_nonclass_method
from tyggbot.models.deck import Deck
from tyggbot.models.command import CommandExample
from tyggbot.models.user import User
from tyggbot.models.duel import UserDuelStats
from tyggbot.models.stream import Stream, StreamChunkHighlight
from tyggbot.models.webcontent import WebContent
from tyggbot.models.time import TimeManager
from tyggbot.models.pleblist import PleblistSong
from tyggbot.models.sock import SocketClientManager
from tyggbot.apiwrappers import TwitchAPI
from tyggbot.tbutil import time_since
from tyggbot.tbutil import find

import markdown
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from flask import request
from flask import render_template
from flask import Markup
from flask import redirect
from flask import url_for
from flask import session
from flask import jsonify
from flask.ext.scrypt import generate_random_salt
from flask_oauthlib.client import OAuth
from flask_oauthlib.client import OAuthException
# from flask import make_response
# from flask import jsonify
from sqlalchemy import func, cast, Date

init_logging('tyggbot')
log = logging.getLogger('tyggbot')

cron = BackgroundScheduler(daemon=True)

cron.start()

app = Flask(__name__)
app._static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
app.register_blueprint(api.page)
app.register_blueprint(admin.page)

config = configparser.ConfigParser()

parser = argparse.ArgumentParser(description='start the web app')
parser.add_argument('--config', default='config.ini')
parser.add_argument('--host', default='0.0.0.0')
parser.add_argument('--port', type=int, default=2325)
parser.add_argument('--debug', dest='debug', action='store_true')
parser.add_argument('--no-debug', dest='debug', action='store_false')
parser.set_defaults(debug=False)

args = parser.parse_args()

config = load_config(args.config)

if 'web' not in config:
    log.error('Missing [web] section in config.ini')
    sys.exit(1)

if 'pleblist_password_salt' not in config['web']:
    salt = generate_random_salt()
    config.set('web', 'pleblist_password_salt', salt.decode('utf-8'))

if 'secret_key' not in config['web']:
    salt = generate_random_salt()
    config.set('web', 'secret_key', salt.decode('utf-8'))

if 'logo' not in config['web']:
    twitchapi = TwitchAPI()
    try:
        data = twitchapi.get(['users', config['main']['streamer']], base='https://api.twitch.tv/kraken/')
        log.info(data)
        if data:
            logo_raw = 'static/images/logo_{}.png'.format(config['main']['streamer'])
            logo_tn = 'static/images/logo_{}_tn.png'.format(config['main']['streamer'])
            with urllib.request.urlopen(data['logo']) as response, open(logo_raw, 'wb') as out_file:
                data = response.read()
                out_file.write(data)
                try:
                    im = Image.open(logo_raw)
                    im.thumbnail((64, 64), Image.ANTIALIAS)
                    im.save(logo_tn, 'png')
                except:
                    log.exception('asd')
            config.set('web', 'logo', 'set')
            log.info('set logo')
    except:
        pass

with open(args.config, 'w') as configfile:
    config.write(configfile)

app.secret_key = config['web']['secret_key']
oauth = OAuth(app)


if 'sock' in config and 'sock_file' in config['sock']:
    SocketClientManager.init(config['sock']['sock_file'])

twitch = oauth.remote_app(
        'twitch',
        consumer_key=config['webtwitchapi']['client_id'],
        consumer_secret=config['webtwitchapi']['client_secret'],
        request_token_params={'scope': 'user_read'},
        base_url='https://api.twitch.tv/kraken/',
        request_token_url=None,
        access_token_method='POST',
        access_token_url='https://api.twitch.tv/kraken/oauth2/token',
        authorize_url='https://api.twitch.tv/kraken/oauth2/authorize',
        )

DBManager.init(config['main']['db'])
TimeManager.init_timezone(config['main'].get('timezone', 'UTC'))

with DBManager.create_session_scope() as db_session:
    num_decks = db_session.query(func.count(Deck.id)).scalar()
    custom_web_content = {}
    for web_content in db_session.query(WebContent).filter(WebContent.content is not None):
        custom_web_content[web_content.page] = web_content.content

has_decks = num_decks > 0

errors.init(app)
api.config = config

modules = config['web'].get('modules', '').split()

bot_commands_list = []

from flask import make_response
from functools import wraps, update_wrapper

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


def update_commands(signal_id):
    global bot_commands_list
    from tyggbot.models.command import CommandManager
    bot_commands = CommandManager(None).load(load_examples=True)
    bot_commands_list = bot_commands.parse_for_web()

    bot_commands_list = sorted(bot_commands_list, key=lambda x: (x.id or -1, x.main_alias))
    del bot_commands

def get_highlight_thumbnails(signal_id):
    with DBManager.create_session_scope() as db_session:
        for highlight in db_session.query(StreamChunkHighlight).filter_by(thumbnail=None):
            if highlight.stream_chunk.video_preview_image_url is not None:
                log.info('Getting thumbnail for highlight {}'.format(highlight.id))
                image_url = highlight.stream_chunk.video_preview_image_url
                out_path = 'static/images/highlights/{}.jpg'.format(highlight.id)
                try:
                    with urllib.request.urlopen(image_url) as response, open(out_path, 'wb') as out_file:
                        data = response.read()
                        out_file.write(data)
                    highlight.thumbnail = True
                    log.info('Finished getting thumbnail for highlight {}'.format(highlight.id))
                except urllib.error.HTTPError:
                    log.info('404d getting thumbnail for highlight {}'.format(highlight.id))
                    highlight.thumbnail = False

update_commands(26)
try:
    import uwsgi
    uwsgi.register_signal(26, "worker", update_commands)
    uwsgi.add_timer(26, 60 * 10)

    uwsgi.register_signal(26, "worker", get_highlight_thumbnails)
    uwsgi.add_timer(27, 10)
except ImportError:
    pass

@app.route('/')
def index():
    custom_content = custom_web_content.get('home', '')
    try:
        custom_content = Markup(markdown.markdown(custom_content))
    except:
        log.exception('Unhandled exception in def index')
    return render_template('index.html',
            custom_content=custom_content)

@app.route('/commands/')
def commands():
    custom_commands = []
    point_commands = []
    moderator_commands = []

    for command in bot_commands_list:
        if command.level > 100 or command.mod_only:
            moderator_commands.append(command)
        elif command.cost > 0:
            point_commands.append(command)
        else:
            custom_commands.append(command)

    return render_template('commands.html',
            custom_commands=sorted(custom_commands, key=lambda f: f.command),
            point_commands=sorted(point_commands, key=lambda a: (a.cost, a.command)),
            moderator_commands=sorted(moderator_commands, key=lambda c: (c.level if c.mod_only is False else 500, c.command)))

@app.route('/commands/<raw_command_string>')
def command_detailed(raw_command_string):
    command_string_parts = raw_command_string.split('-')
    command_string = command_string_parts[0]
    command_id = None
    try:
        command_id = int(command_string)
    except ValueError:
        pass

    if command_id is not None:
        command = find(lambda c: c.id == command_id, bot_commands_list)
    else:
        command = find(lambda c: c.resolve_string == command_string, bot_commands_list)

    if command is None:
        # XXX: Is it proper to have it return a 404 code as well?
        return render_template('command_404.html')

    examples = command.autogenerate_examples()

    return render_template('command_detailed.html', command=command, examples=examples)

@app.route('/decks/')
def decks():
    session = DBManager.create_session()
    top_decks = []
    for deck in session.query(Deck).order_by(Deck.last_used.desc(), Deck.first_used.desc())[:25]:
        top_decks.append(deck)
    session.close()
    return render_template('decks/all.html',
            top_decks=top_decks,
            deck_class=None)

@app.route('/decks/druid/')
def decks_druid():
    session = DBManager.create_session()
    decks = session.query(Deck).filter_by(deck_class='druid').order_by(Deck.last_used.desc(), Deck.first_used.desc()).all()
    session.close()
    return render_template('decks/by_class.html',
            decks=decks,
            deck_class='Druid')

@app.route('/decks/hunter/')
def decks_hunter():
    session = DBManager.create_session()
    decks = session.query(Deck).filter_by(deck_class='hunter').order_by(Deck.last_used.desc(), Deck.first_used.desc()).all()
    session.close()
    return render_template('decks/by_class.html',
            decks=decks,
            deck_class='Hunter')

@app.route('/decks/mage/')
def decks_mage():
    session = DBManager.create_session()
    decks = session.query(Deck).filter_by(deck_class='mage').order_by(Deck.last_used.desc(), Deck.first_used.desc()).all()
    session.close()
    return render_template('decks/by_class.html',
            decks=decks,
            deck_class='Mage')

@app.route('/decks/paladin/')
def decks_paladin():
    session = DBManager.create_session()
    decks = session.query(Deck).filter_by(deck_class='paladin').order_by(Deck.last_used.desc(), Deck.first_used.desc()).all()
    session.close()
    return render_template('decks/by_class.html',
            decks=decks,
            deck_class='Paladin')

@app.route('/decks/priest/')
def decks_priest():
    session = DBManager.create_session()
    decks = session.query(Deck).filter_by(deck_class='priest').order_by(Deck.last_used.desc(), Deck.first_used.desc()).all()
    session.close()
    return render_template('decks/by_class.html',
            decks=decks,
            deck_class='Priest')

@app.route('/decks/rogue/')
def decks_rogue():
    session = DBManager.create_session()
    decks = session.query(Deck).filter_by(deck_class='rogue').order_by(Deck.last_used.desc(), Deck.first_used.desc()).all()
    session.close()
    return render_template('decks/by_class.html',
            decks=decks,
            deck_class='Rogue')

@app.route('/decks/shaman/')
def decks_shaman():
    session = DBManager.create_session()
    decks = session.query(Deck).filter_by(deck_class='shaman').order_by(Deck.last_used.desc(), Deck.first_used.desc()).all()
    session.close()
    return render_template('decks/by_class.html',
            decks=decks,
            deck_class='Shaman')

@app.route('/decks/warlock/')
def decks_warlock():
    session = DBManager.create_session()
    decks = session.query(Deck).filter_by(deck_class='warlock').order_by(Deck.last_used.desc(), Deck.first_used.desc()).all()
    session.close()
    return render_template('decks/by_class.html',
            decks=decks,
            deck_class='Warlock')

@app.route('/decks/warrior/')
def decks_warrior():
    session = DBManager.create_session()
    decks = session.query(Deck).filter_by(deck_class='warrior').order_by(Deck.last_used.desc(), Deck.first_used.desc()).all()
    session.close()
    return render_template('decks/by_class.html',
            decks=decks,
            deck_class='Warrior')

@app.route('/user/<username>')
def user_profile(username):
    session = DBManager.create_session()
    user = session.query(User).filter_by(username=username).one_or_none()
    if user is None:
        return render_template('no_user.html'), 404

    rank = session.query(func.Count(User.id)).filter(User.points > user.points).one()
    rank = rank[0] + 1
    user.rank = rank

    user_duel_stats = session.query(UserDuelStats).filter_by(user_id=user.id).one_or_none()

    try:
        return render_template('user.html',
                user=user,
                user_duel_stats=user_duel_stats)
    finally:
        session.close()


@app.route('/points/')
def points():
    custom_content = custom_web_content.get('points', '')
    try:
        custom_content = Markup(markdown.markdown(custom_content))
    except:
        log.exception('Unhandled exception in def index')
    session = DBManager.create_session()
    top_30_users = []
    for user in session.query(User).order_by(User.points.desc())[:30]:
        top_30_users.append(user)
    session.close()
    return render_template('points.html',
            top_30_users=top_30_users,
            custom_content=custom_content)


@app.route('/debug')
def debug():
    return render_template('debug.html')


@app.route('/stats/')
def stats():
    top_5_commands = sorted(bot_commands_list, key=lambda c: c.data.num_uses if c.data is not None else -1, reverse=True)[:5]

    if 'linefarming' in modules:
        session = DBManager.create_session()
        top_5_line_farmers = session.query(User).order_by(User.num_lines.desc())[:5]
        session.close()
    else:
        top_5_line_farmers = []

    return render_template('stats.html',
            top_5_commands=top_5_commands,
            top_5_line_farmers=top_5_line_farmers)

@app.route('/stats/duels/')
def stats_duels():
    session = DBManager.create_session()

    data = {
            'top_5_winners': session.query(UserDuelStats).order_by(UserDuelStats.duels_won.desc())[:5],
            'top_5_points_won': session.query(UserDuelStats).order_by(UserDuelStats.profit.desc())[:5],
            'top_5_points_lost': session.query(UserDuelStats).order_by(UserDuelStats.profit.asc())[:5],
            'top_5_losers': session.query(UserDuelStats).order_by(UserDuelStats.duels_lost.desc())[:5],
            'top_5_winrate': session.query(UserDuelStats).filter(UserDuelStats.duels_won >= 5).order_by(UserDuelStats.winrate.desc())[:5],
            'bottom_5_winrate': session.query(UserDuelStats).filter(UserDuelStats.duels_lost >= 5).order_by(UserDuelStats.winrate.asc())[:5],
            }

    try:
        return render_template('stats_duels.html', **data)
    finally:
        session.close()

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/highlights/<date>/')
def highlight_list_date(date):
    # Make sure we were passed a valid date
    try:
        parsed_date = datetime.datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        # Invalid date
        return redirect('/highlights/', 303)
    session = DBManager.create_session()
    dates_with_highlights = []
    highlights = session.query(StreamChunkHighlight).filter(cast(StreamChunkHighlight.created_at, Date) == parsed_date).order_by(StreamChunkHighlight.created_at.desc()).all()
    for highlight in session.query(StreamChunkHighlight):
        dates_with_highlights.append(datetime.datetime(
            year=highlight.created_at.year,
            month=highlight.created_at.month,
            day=highlight.created_at.day))

    try:
        return render_template('highlights_date.html',
                highlights=highlights,
                date=parsed_date,
                dates_with_highlights=set(dates_with_highlights))
    finally:
        session.close()

@app.route('/highlights/<date>/<highlight_id>', defaults={'highlight_title': None})
@app.route('/highlights/<date>/<highlight_id>-<highlight_title>')
def highlight_id(date, highlight_id, highlight_title=None):
    session = DBManager.create_session()
    highlight = session.query(StreamChunkHighlight).filter_by(id=highlight_id).first()
    if highlight is None:
        session.close()
        return render_template('highlight_404.html'), 404
    else:
        stream_chunk = highlight.stream_chunk
        stream = stream_chunk.stream
        session.close()
    return render_template('highlight.html',
            highlight=highlight,
            stream_chunk=stream_chunk,
            stream=stream)

@app.route('/highlights/')
def highlights():
    session = DBManager.create_session()
    dates_with_highlights = []
    highlights = session.query(StreamChunkHighlight).order_by(StreamChunkHighlight.created_at.desc()).all()
    for highlight in highlights:
        dates_with_highlights.append(datetime.datetime(
            year=highlight.created_at.year,
            month=highlight.created_at.month,
            day=highlight.created_at.day))
    try:
        return render_template('highlights.html',
                highlights=highlights[:5],
                dates_with_highlights=set(dates_with_highlights))
    finally:
        session.close()


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

@app.route('/pleblist/history/<stream_id>/')
def pleblist_history_stream(stream_id):
    with DBManager.create_session_scope() as session:
        stream = session.query(Stream).filter_by(id=stream_id).one_or_none()
        if stream is None:
            return render_template('pleblist_history_404.html'), 404

        songs = session.query(PleblistSong).filter(PleblistSong.stream_id == stream.id).order_by(PleblistSong.date_added.asc(), PleblistSong.date_played.asc()).all()
        total_length_left = sum([song.song_info.duration if song.date_played is None and song.song_info is not None else 0 for song in songs])

        return render_template('pleblist_history.html',
                stream=stream,
                songs=songs,
                total_length_left=total_length_left)


@app.route('/discord')
def discord():
    return render_template('discord.html')


@app.route('/clr/overlay/<widget_id>')
@nocache
def clr_overlay(widget_id):
    if widget_id == config['web']['clr_widget_id'] or True:
        return render_template('clr/overlay.html',
                widget={})
    else:
        return render_template('errors/404.html'), 404

@app.route('/login')
def login():
    return twitch.authorize(callback=config['webtwitchapi']['redirect_uri'] if 'redirect_uri' in config['webtwitchapi'] else url_for('authorized', _external=True))

@app.route('/login/error')
def login_error():
    return render_template('login_error.html')

@app.route('/login/authorized')
def authorized():
    try:
        resp = twitch.authorized_response()
    except OAuthException:
        log.exception('An exception was caught while authorizing')
        return redirect(url_for('index'))

    print(resp)
    if resp is None:
        log.warn('Access denied: reason={}, error={}'.format(request.args['error'], request.args['error_description']))
        return redirect(url_for('index'))
    elif type(resp) is OAuthException:
        log.warn(resp.message)
        log.warn(resp.data)
        log.warn(resp.type)
        return redirect(url_for('login_error'))
    session['twitch_token'] = (resp['access_token'], )
    me = twitch.get('user')
    session['user'] = {
            'username': me.data['name'],
            'username_raw': me.data['display_name'],
            }
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('twitch_token', None)
    session.pop('user', None)
    return redirect(url_for('index'))

@twitch.tokengetter
def get_twitch_oauth_token():
    return session.get('twitch_token')

def change_twitch_header(uri, headers, body):
    auth = headers.get('Authorization')
    if auth:
        auth = auth.replace('Bearer', 'OAuth')
        headers['Authorization'] = auth
    return uri, headers, body

twitch.pre_request = change_twitch_header

@app.template_filter()
def date_format(value, format='full'):
    if format == 'full':
        date_format = '%Y-%m-%d %H:%M:%S'

    return value.strftime(date_format)

@app.template_filter('strftime')
def time_strftime(value, format):
    return value.strftime(format)

@app.template_filter('localize')
def time_localize(value):
    return TimeManager.localize(value)

@app.template_filter('unix_timestamp')
def time_unix_timestamp(value):
    return value.timestamp()

@app.template_filter()
def number_format(value, tsep=',', dsep='.'):
    s = str(value)
    cnt = 0
    numchars = dsep + '0123456789'
    ls = len(s)
    while cnt < ls and s[cnt] not in numchars:
        cnt += 1

    lhs = s[:cnt]
    s = s[cnt:]
    if not dsep:
        cnt = -1
    else:
        cnt = s.rfind(dsep)
    if cnt > 0:
        rhs = dsep + s[cnt + 1:]
        s = s[:cnt]
    else:
        rhs = ''

    splt = ''
    while s != '':
        splt = s[-3:] + tsep + splt
        s = s[:-3]

    return lhs + splt[:-1] + rhs


nav_bar_header = []
nav_bar_header.append(('/', 'home', 'Home'))
nav_bar_header.append(('/commands/', 'commands', 'Commands'))
if has_decks:
    nav_bar_header.append(('/decks/', 'decks', 'Decks'))
nav_bar_header.append(('/points/', 'points', 'Points'))
nav_bar_header.append(('/stats/', 'stats', 'Stats'))
nav_bar_header.append(('/highlights/', 'highlights', 'Highlights'))
if 'pleblist' in modules:
    nav_bar_header.append(('/pleblist/history/', 'pleblist', 'Pleblist'))

nav_bar_admin_header = []
nav_bar_admin_header.append(('/', 'home', 'Home'))
nav_bar_admin_header.append(('/admin/', 'admin_home', 'Admin Home'))
nav_bar_admin_header.append(('/admin/banphrases/', 'admin_banphrases', 'Banphrases'))
nav_bar_admin_header.append(('/admin/commands/', 'admin_commands', 'Commands'))
nav_bar_admin_header.append(('/admin/links/blacklist/', 'admin_links_blacklist', 'Blacklisted links'))
nav_bar_admin_header.append(('/admin/links/whitelist/', 'admin_links_whitelist', 'Whitelisted links'))

version = TyggBot.version
last_commit = ''
commit_number = 0
try:
    current_branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode('utf8').strip()
    latest_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf8').strip()[:8]
    commit_number = subprocess.check_output(['git', 'rev-list', 'HEAD', '--count']).decode('utf8').strip()
    last_commit = subprocess.check_output(['git', 'log', '-1', '--format=%cd']).decode('utf8').strip()
    version = '{0} DEV ({1}, {2}, commit {3})'.format(version, current_branch, latest_commit, commit_number)
except:
    pass


default_variables = {
        'version': version,
        'last_commit': last_commit,
        'commit_number': commit_number,
        'bot': {
            'name': config['main']['nickname'],
            },
        'site': {
            'domain': config['web']['domain'],
            'deck_tab_images': config.getboolean('web', 'deck_tab_images'),
            'websocket': {
                'port': config['websocket']['port'],
                'ssl': config.getboolean('websocket', 'ssl')
                }
            },
        'streamer': {
            'name': config['web']['streamer_name'],
            'full_name': config['main']['streamer']
            },
        'has_decks': has_decks,
        'nav_bar_header': nav_bar_header,
        'nav_bar_admin_header': nav_bar_admin_header,
        'modules': modules,
        'current_time': datetime.datetime.now(),
        'request': request,
        'session': session,
        }

if 'streamtip' in config:
    default_variables['streamtip_data'] = {
            'client_id': config['streamtip']['client_id'],
            'redirect_uri': config['streamtip']['redirect_uri'],
            }


@app.context_processor
def inject_default_variables():
    return default_variables

@app.template_filter('time_ago')
def time_ago(t, format='long'):
    return time_since(datetime.datetime.now().timestamp(), t.timestamp(), format)

@app.template_filter('time_diff')
def time_diff(t1, t2, format='long'):
    return time_since(t1.timestamp(), t2.timestamp(), format)

@app.template_filter('time_ago_timespan_seconds')
def time_ago_timespan_seconds(t, format='long'):
    v = time_since(t, 0, format)
    return 'None' if len(v) == 0 else v

if __name__ == '__main__':
    app.run(debug=args.debug, host=args.host, port=args.port)
