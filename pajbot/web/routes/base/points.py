import logging

import markdown
from flask import Markup
from flask import render_template

from pajbot.managers import DBManager
from pajbot.models.user import User
from pajbot.models.webcontent import WebContent

log = logging.getLogger(__name__)

def init(app):
    @app.route('/points/')
    def points():
        with DBManager.create_session_scope() as db_session:
            custom_web_content = db_session.query(WebContent).filter_by(page='points').first()
            custom_content = ''
            if custom_web_content and custom_web_content.content:
                try:
                    custom_content = Markup(markdown.markdown(custom_web_content.content))
                except:
                    log.exception('Unhandled exception in def index')

            return render_template('points.html',
                    top_30_users=db_session.query(User).order_by(User.points.desc()).limit(30),
                    custom_content=custom_content)
