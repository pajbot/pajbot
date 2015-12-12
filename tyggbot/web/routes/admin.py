import datetime
import base64
import binascii
import logging

from tyggbot.models.filter import Filter
from tyggbot.models.linkchecker import BlacklistedLink
from tyggbot.models.linkchecker import WhitelistedLink
from tyggbot.models.user import User
from tyggbot.models.db import DBManager

import requests
from flask import Blueprint
from flask import jsonify
from flask import make_response
from flask import request
from flask import redirect
from flask import session
from flask import render_template
from flask import abort
from flask.ext.scrypt import generate_password_hash
from flask.ext.scrypt import check_password_hash
from sqlalchemy import func
from sqlalchemy import and_


from functools import wraps, update_wrapper


page = Blueprint('admin', __name__, url_prefix='/admin')

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

            return f(*args, **kwargs)
        return update_wrapper(decorated_function, f)
    return decorator

@page.route('/')
@requires_level(500)
def home():
    return render_template('admin/home.html')

@page.route('/banphrases/')
@requires_level(500)
def banphrases():
    with DBManager.create_session_scope() as db_session:
        banphrases = db_session.query(Filter).filter_by(enabled=True, type='banphrase').all()
        return render_template('admin/banphrases.html',
                banphrases=banphrases)

@page.route('/links/blacklist/')
@requires_level(500)
def links_blacklist():
    with DBManager.create_session_scope() as db_session:
        links = db_session.query(BlacklistedLink).filter_by().all()
        return render_template('admin/links_blacklist.html',
                links=links)

@page.route('/links/whitelist/')
@requires_level(500)
def links_whitelist():
    with DBManager.create_session_scope() as db_session:
        links = db_session.query(WhitelistedLink).filter_by().all()
        return render_template('admin/links_whitelist.html',
                links=links)
