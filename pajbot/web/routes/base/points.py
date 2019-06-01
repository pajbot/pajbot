import logging

import markdown
from flask import Markup
from flask import render_template

from pajbot.managers.db import DBManager
from pajbot.models.user import User
from pajbot.models.webcontent import WebContent

log = logging.getLogger(__name__)


def init(app):
    @app.route("/points")
    def points():
        with DBManager.create_session_scope() as db_session:
            custom_web_content = db_session.query(WebContent).filter_by(page="points").first()
            custom_content = ""
            if custom_web_content and custom_web_content.content:
                try:
                    custom_content = Markup(markdown.markdown(custom_web_content.content))
                except:
                    log.exception("Unhandled exception in def index")

            rank = 1
            index = 1
            last_user_points = -13333337
            rankings = []
            for user in db_session.query(User).order_by(User.points.desc()).limit(30):
                if user.points != last_user_points:
                    rank = index

                rankings.append((rank, user))

                index += 1
                last_user_points = user.points

            return render_template("points.html", top_30_users=rankings, custom_content=custom_content)
