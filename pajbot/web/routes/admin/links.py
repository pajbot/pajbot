from pajbot.managers.db import DBManager
from pajbot.modules.linkchecker import BlacklistedLink, WhitelistedLink
from pajbot.web.utils import requires_level

from flask import render_template
from flask.typing import ResponseReturnValue


def init(page) -> None:
    @page.route("/links/blacklist/")
    @requires_level(500)
    def links_blacklist(**options) -> ResponseReturnValue:
        with DBManager.create_session_scope() as db_session:
            links = db_session.query(BlacklistedLink).filter_by().all()
            return render_template("admin/links_blacklist.html", links=links)

    @page.route("/links/whitelist/")
    @requires_level(500)
    def links_whitelist(**options) -> ResponseReturnValue:
        with DBManager.create_session_scope() as db_session:
            links = db_session.query(WhitelistedLink).filter_by().all()
            return render_template("admin/links_whitelist.html", links=links)
