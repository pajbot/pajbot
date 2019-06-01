from flask import render_template

from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import DBManager
from pajbot.models.user import User
from pajbot.web.utils import requires_level


def init(page):
    @page.route("/")
    @requires_level(500)
    def home(**options):
        latest_logs_raw = AdminLogManager.get_entries()
        cached_users = {}
        with DBManager.create_session_scope() as db_session:
            latest_logs = []
            for log in latest_logs_raw:
                log["user"] = (
                    cached_users[log["user_id"]]
                    if log["user_id"] in cached_users
                    else db_session.query(User).filter_by(id=log["user_id"]).one_or_none()
                )
                latest_logs.append(log)

            return render_template("admin/home.html", latest_logs=latest_logs)
