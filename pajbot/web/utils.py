import datetime
import logging
from functools import update_wrapper
from functools import wraps

from flask import abort
from flask import make_response
from flask import session

from pajbot.models.db import DBManager
from pajbot.models.user import User

log = logging.getLogger(__name__)

def requires_level(level):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                abort(403)
            with DBManager.create_session_scope() as db_session:
                user = db_session.query(User).filter_by(username=session['user']['username']).one_or_none()
                if user is None:
                    abort(403)

                if user.level < level:
                    abort(403)

                db_session.expunge(user)
                kwargs['user'] = user

            return f(*args, **kwargs)
        return update_wrapper(decorated_function, f)
    return decorator

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

def download_logo(streamer):
    import urllib
    from pajbot.apiwrappers import TwitchAPI

    twitchapi = TwitchAPI()
    try:
        data = twitchapi.get(['users', streamer], base='https://api.twitch.tv/kraken/')
        log.info(data)
        if data:
            logo_raw = 'static/images/logo_{}.png'.format(streamer)
            logo_tn = 'static/images/logo_{}_tn.png'.format(streamer)
            with urllib.request.urlopen(data['logo']) as response, open(logo_raw, 'wb') as out_file:
                data = response.read()
                out_file.write(data)
                try:
                    from PIL import Image
                    im = Image.open(logo_raw)
                    im.thumbnail((64, 64), Image.ANTIALIAS)
                    im.save(logo_tn, 'png')
                except:
                    log.exception('Unhandled exception in download_logo PIL shit')
            log.info('set logo')
            return True
    except:
        log.exception('Unhandled exception in download_logo')
    return False
