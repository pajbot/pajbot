import logging

from flask import Blueprint
from flask import render_template

from pajbot.web.utils import nocache

page = Blueprint("clr", __name__, url_prefix="/clr")
config = None

log = logging.getLogger("pajbot")


@page.route("/overlay/<widget_id>")
@page.route("/overlay/<widget_id>/<salt>")
@nocache
def overlay(widget_id, salt):
    return render_template("clr/overlay.html", data={"id": widget_id, "salt": salt})
