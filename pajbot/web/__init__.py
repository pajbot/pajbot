import os

from flask import Flask

app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__ + '/../..')), 'static'),
        template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__ + '/../..')), 'templates'),
        )


def init(args):
    import configparser
    import datetime
    import logging
    import subprocess
    import sys

    from flask import request
    from flask import session
    from flask_scrypt import generate_random_salt

    import pajbot.web.common
    import pajbot.web.routes
    from pajbot.bot import Bot
    from pajbot.managers.db import DBManager
    from pajbot.managers.redis import RedisManager
    from pajbot.managers.time import TimeManager
    from pajbot.models.module import ModuleManager
    from pajbot.models.sock import SocketClientManager
    from pajbot.streamhelper import StreamHelper
    from pajbot.utils import load_config
    from pajbot.web.models import errors
    from pajbot.web.utils import download_logo

    log = logging.getLogger(__name__)

    config = configparser.ConfigParser()

    config = load_config(args.config)
    config.read('webconfig.ini')

    if 'web' not in config:
        log.error('Missing [web] section in config.ini')
        sys.exit(1)

    if 'pleblist_password_salt' not in config['web']:
        salt = generate_random_salt()
        config.set('web', 'pleblist_password_salt', salt.decode('utf-8'))

    if 'pleblist_password' not in config['web']:
        salt = generate_random_salt()
        config.set('web', 'pleblist_password', salt.decode('utf-8'))

    if 'secret_key' not in config['web']:
        salt = generate_random_salt()
        config.set('web', 'secret_key', salt.decode('utf-8'))

    if 'logo' not in config['web']:
        res = download_logo(config['webtwitchapi']['client_id'], config['main']['streamer'])
        if res:
            config.set('web', 'logo', 'set')

    StreamHelper.init_web(config['main']['streamer'])

    redis_options = {}
    if 'redis' in config:
        redis_options = config._sections['redis']

    RedisManager.init(**redis_options)

    with open(args.config, 'w') as configfile:
        config.write(configfile)

    app.bot_modules = config['web'].get('modules', '').split()
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
    pajbot.web.common.menu.init(app)

    app.register_blueprint(pajbot.web.routes.clr.page)

    errors.init(app)
    pajbot.web.routes.clr.config = config

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
            'modules': app.bot_modules,
            'request': request,
            'session': session,
            'google_analytics': config['web'].get('google_analytics', None),
            }

    @app.context_processor
    def current_time():
        current_time = {}
        current_time['current_time'] = datetime.datetime.now()
        return current_time

    @app.context_processor
    def inject_default_variables():
        return default_variables
