import logging

from pajbot.managers.db import DBManager
from pajbot.models.user import User
from pajbot.models.webcontent import WebContent
from pajbot.modules import ChattersRefreshModule

import markdown
from flask import render_template
from markupsafe import Markup
from sqlalchemy import column, text

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
            # note on the efficiency of this query: takes approx. 0.3-0.4 milliseconds on a 5 million user DB
            #
            # pajbot=# EXPLAIN ANALYZE SELECT * FROM (SELECT *, rank() OVER (ORDER BY points DESC) AS rank FROM "user") AS subquery LIMIT 30;
            #                                                                         QUERY PLAN
            # ----------------------------------------------------------------------------------------------------------------------------------------------------------
            #  Limit  (cost=0.43..2.03 rows=30 width=49) (actual time=0.020..0.069 rows=30 loops=1)
            #    ->  WindowAgg  (cost=0.43..181912.19 rows=4197554 width=49) (actual time=0.020..0.065 rows=30 loops=1)
            #          ->  Index Scan Backward using user_points_idx on "user"  (cost=0.43..118948.88 rows=4197554 width=41) (actual time=0.012..0.037 rows=31 loops=1)
            #  Planning Time: 0.080 ms
            #  Execution Time: 0.089 ms
            #
            # (see also the extensive comment on migration revision ID 2, 0002_create_index_on_user_points.py)
            rankings = db_session.query(User, column("rank")).from_statement(
                text(
                    'SELECT * FROM (SELECT *, rank() OVER (ORDER BY points DESC) AS rank FROM "user") AS subquery LIMIT 30'
                )
            )

            chatters_refresh_enabled = ChattersRefreshModule.is_enabled()
            chatters_refresh_settings = ChattersRefreshModule.module_settings()
            chatters_refresh_interval = ChattersRefreshModule.UPDATE_INTERVAL

            return render_template(
                "points.html",
                top_30_users=rankings,
                custom_content=custom_content,
                chatters_refresh_enabled=chatters_refresh_enabled,
                chatters_refresh_settings=chatters_refresh_settings,
                chatters_refresh_interval=chatters_refresh_interval,
            )
