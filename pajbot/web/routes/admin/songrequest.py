import logging
import time

from flask import redirect
from flask import session
from flask import render_template

from pajbot.web.utils import requires_level

log = logging.getLogger(__name__)

def init(page):
    @page.route("/songrequest")
    @requires_level(500)
    def admin_songrequest(**options):
        if session.get("twitch_token_expire", 0) <= round(time.time()):
            return redirect("/login?n=/admin/songrequest")
        return render_template("admin/songrequest.html", token_access=session.get("twitch_token"))
