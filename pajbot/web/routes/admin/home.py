from pajbot.managers.adminlog import AdminLogEntry
from pajbot.managers.db import DBManager
from pajbot.web.utils import requires_level

from flask import render_template
from flask.typing import ResponseReturnValue
from sqlalchemy.orm import joinedload


def init(page) -> None:
    @page.route("/")
    @requires_level(500)
    def home(**options) -> ResponseReturnValue:
        with DBManager.create_session_scope() as db_session:
            latest_logs = (
                db_session.query(AdminLogEntry)
                .options(joinedload("user"))
                .order_by(AdminLogEntry.created_at.desc())
                .limit(50)
                .all()
            )
            return render_template("admin/home.html", latest_logs=latest_logs)
