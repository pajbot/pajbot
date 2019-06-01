import logging

from flask import Blueprint
from flask import render_template

from pajbot.web.utils import nocache

page = Blueprint("clr", __name__, url_prefix="/clr")
config = None

log = logging.getLogger("pajbot")


@page.route("/overlay/<widget_id>")
@page.route("/overlay/<widget_id>/<random_shit>")
@nocache
def overlay(widget_id, **options):
    return render_template("clr/overlay.html", widget={})


@page.route("/fatoverlay/<widget_id>")
@page.route("/fatoverlay/<widget_id>/<random_shit>")
@nocache
def fatoverlay(widget_id, **options):
    return render_template("clr/fatoverlay.html", widget={})


@page.route("/crazyoverlay/<widget_id>")
@page.route("/crazyoverlay/<widget_id>/<random_shit>")
@nocache
def crazyoverlay(widget_id, **options):
    return render_template("clr/crazyoverlay.html", widget={})
