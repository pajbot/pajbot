from functools import wraps, update_wrapper

from pajbot.models.user import User
from pajbot.models.db import DBManager

from flask import session
from flask import abort

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
