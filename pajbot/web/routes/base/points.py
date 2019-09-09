import logging

import markdown
from flask import Markup
from flask import render_template
from sqlalchemy import text

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

            # rankings is a list of (User, int) tuples (user with their rank)
            rankings = db_session.query(User, "rank").from_statement(
                text(
                    'SELECT * FROM (SELECT *, rank() OVER (ORDER BY points DESC) AS rank FROM "user") AS subquery LIMIT 30'
                )
            )

            return render_template("points.html", top_30_users=rankings, custom_content=custom_content)
