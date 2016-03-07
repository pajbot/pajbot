#!/usr/bin/env python3

import argparse
import configparser
import datetime
import logging
import os
import subprocess
import sys
import urllib

from pajbot.apiwrappers import TwitchAPI
from pajbot.bot import Bot
from pajbot.managers import RedisManager
from pajbot.models.db import DBManager
from pajbot.models.module import ModuleManager
from pajbot.models.sock import SocketClientManager
from pajbot.models.time import TimeManager
from pajbot.streamhelper import StreamHelper
from pajbot.tbutil import load_config, init_logging
from pajbot.web.models import errors
import pajbot.web.routes
import pajbot.web.common

from flask import Flask
from flask import request
from flask import session
from flask.ext.scrypt import generate_random_salt

init_logging('pajbot')
log = logging.getLogger('pajbot')

app = Flask(__name__)
app._static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

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
config.read('webconfig.ini')

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
                    from PIL import Image
                    im = Image.open(logo_raw)
                    im.thumbnail((64, 64), Image.ANTIALIAS)
                    im.save(logo_tn, 'png')
                except:
                    pass
            config.set('web', 'logo', 'set')
            log.info('set logo')
    except:
        pass

StreamHelper.init_web(config['main']['streamer'])

redis_options = {}
if 'redis' in config:
    redis_options = config._sections['redis']

RedisManager.init(**redis_options)

with open(args.config, 'w') as configfile:
    config.write(configfile)

app.bot_commands_list = []
app.bot_config = config
app.secret_key = config['web']['secret_key']


if 'sock' in config and 'sock_file' in config['sock']:
    SocketClientManager.init(config['sock']['sock_file'])


DBManager.init(config['main']['db'])
TimeManager.init_timezone(config['main'].get('timezone', 'UTC'))

app.module_manager = ModuleManager(None).load()


pajbot.web.routes.admin.init(app)
pajbot.web.routes.api.init(app)
pajbot.web.routes.base.init(app)

pajbot.web.common.filters.init(app)
pajbot.web.common.assets.init(app)
pajbot.web.common.tasks.init(app)

app.register_blueprint(pajbot.web.routes.clr.page)
app.register_blueprint(pajbot.web.routes.api.page)

errors.init(app)
pajbot.web.routes.api.config = config
pajbot.web.routes.clr.config = config

modules = config['web'].get('modules', '').split()

nav_bar_header = []
nav_bar_header.append(('/', 'home', 'Home'))
nav_bar_header.append(('/commands/', 'commands', 'Commands'))
if 'deck' in app.module_manager:
    nav_bar_header.append(('/decks/', 'decks', 'Decks'))
if config['main']['nickname'] not in ['scamazbot']:
    nav_bar_header.append(('/points/', 'points', 'Points'))
nav_bar_header.append(('/stats/', 'stats', 'Stats'))
nav_bar_header.append(('/highlights/', 'highlights', 'Highlights'))
if 'pleblist' in modules:
    nav_bar_header.append(('/pleblist/history/', 'pleblist', 'Pleblist'))

nav_bar_admin_header = []
nav_bar_admin_header.append(('/', 'home', 'Home'))
nav_bar_admin_header.append(('/admin/', 'admin_home', 'Admin Home'))
nav_bar_admin_header.append(([
    ('/admin/banphrases/', 'admin_banphrases', 'Banphrases'),
    ('/admin/links/blacklist/', 'admin_links_blacklist', 'Blacklisted links'),
    ('/admin/links/whitelist/', 'admin_links_whitelist', 'Whitelisted links'),
    ], None, 'Filters'))
nav_bar_admin_header.append(('/admin/commands/', 'admin_commands', 'Commands'))
nav_bar_admin_header.append(('/admin/timers/', 'admin_timers', 'Timers'))
nav_bar_admin_header.append(('/admin/moderators/', 'admin_moderators', 'Moderators'))
nav_bar_admin_header.append(('/admin/modules/', 'admin_modules', 'Modules'))
if 'predict' in app.module_manager:
    nav_bar_admin_header.append(('/admin/predictions/', 'admin_predictions', 'Predictions'))
nav_bar_admin_header.append(('/admin/streamer/', 'admin_streamer', 'Streamer Info'))
nav_bar_admin_header.append(('/admin/clr/', 'admin_clr', 'CLR'))

version = Bot.version
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
                'host': config['websocket'].get('host', config['web']['domain']),
                'port': config['websocket']['port'],
                'ssl': config.getboolean('websocket', 'ssl')
                }
            },
        'streamer': {
            'name': config['web']['streamer_name'],
            'full_name': config['main']['streamer']
            },
        'nav_bar_header': nav_bar_header,
        'nav_bar_admin_header': nav_bar_admin_header,
        'modules': modules,
        'request': request,
        'session': session,
        'google_analytics': config['web'].get('google_analytics', None),
        }

if 'streamtip' in config:
    default_variables['streamtip_data'] = {
            'client_id': config['streamtip']['client_id'],
            'redirect_uri': config['streamtip']['redirect_uri'],
            }
else:
    default_variables['streamtip_data'] = {
            'client_id': 'MISSING',
            'redirect_uri': 'MISSING',
            }

if 'twitchalerts' in config:
    default_variables['twitchalerts_data'] = {
            'client_id': config['twitchalerts']['client_id'],
            'redirect_uri': config['twitchalerts']['redirect_uri'],
            }
else:
    default_variables['twitchalerts_data'] = {
            'client_id': 'MISSING',
            'redirect_uri': 'MISSING',
            }

@app.context_processor
def current_time():
    current_time = {}
    current_time['current_time'] = datetime.datetime.now()
    return current_time

@app.context_processor
def inject_default_variables():
    return default_variables

if __name__ == '__main__':
    app.run(debug=args.debug, host=args.host, port=args.port)
