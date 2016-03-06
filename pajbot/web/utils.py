import datetime
from functools import wraps, update_wrapper

from pajbot.models.user import User
from pajbot.models.db import DBManager

from flask import session
from flask import abort
from flask import make_response

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
