import logging

from flask import Blueprint
from flask import render_template

from pajbot.managers.db import DBManager
from pajbot.models.web_sockets import WebSocket
from pajbot.web.utils import nocache

page = Blueprint("clr", __name__, url_prefix="/clr")
config = None

log = logging.getLogger("pajbot")

@page.route("/overlay/<salt>")
@nocache
def overlay(salt):
    with DBManager.create_session_scope() as db_session:
        if not WebSocket._by_salt(db_session, salt):
            return render_template("no_overlay.html"), 404
    return render_template("clr/overlay.html", salt=salt)
