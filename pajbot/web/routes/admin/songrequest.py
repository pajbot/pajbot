import logging
from datetime import datetime

from flask import redirect
from flask import session
from flask import render_template

from pajbot.web.utils import requires_level
from pajbot import utils

log = logging.getLogger(__name__)


def init(page):
    @page.route("/songrequest")
    @requires_level(500)
    def admin_songrequest(**options):
        token_expire = session.get("twitch_token_expire")
        if not token_expire or token_expire <= datetime.timestamp(utils.now()):
            return redirect("/login?returnTo=/admin/songrequest")
        return render_template("admin/songrequest.html", token_access=session.get("twitch_token"))
