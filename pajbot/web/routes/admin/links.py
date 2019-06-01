from flask import render_template

from pajbot.managers.db import DBManager
from pajbot.modules.linkchecker import BlacklistedLink
from pajbot.modules.linkchecker import WhitelistedLink
from pajbot.web.utils import requires_level


def init(page):
    @page.route("/links/blacklist/")
    @requires_level(500)
    def links_blacklist(**options):
        with DBManager.create_session_scope() as db_session:
            links = db_session.query(BlacklistedLink).filter_by().all()
            return render_template("admin/links_blacklist.html", links=links)

    @page.route("/links/whitelist/")
    @requires_level(500)
    def links_whitelist(**options):
        with DBManager.create_session_scope() as db_session:
            links = db_session.query(WhitelistedLink).filter_by().all()
            return render_template("admin/links_whitelist.html", links=links)
