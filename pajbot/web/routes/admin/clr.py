import binascii
import json
import logging
import os

from flask import render_template

from pajbot.managers.redis import RedisManager
from pajbot.streamhelper import StreamHelper
from pajbot.web.utils import requires_level

log = logging.getLogger(__name__)


def init(page):
    @page.route("/clr/")
    @requires_level(500)
    def clr_home(**options):
        return render_template("admin/clr/home.html")

    @page.route("/clr/donations/")
    @requires_level(1500)
    def clr_donations_home(**options):
        redis = RedisManager.get()
        key = "{streamer}:clr:donations".format(streamer=StreamHelper.get_streamer())
        widgets = redis.hgetall(key)

        # Make sure all the widget data is converted from a string to a dictionary
        for widget_id in widgets:
            widgets[widget_id] = json.loads(widgets[widget_id])

        new_widget_id = None
        while new_widget_id is None or new_widget_id in widgets:
            new_widget_id = binascii.hexlify(os.urandom(32)).decode("utf8").upper()

        return render_template("admin/clr/donations/home.html", widgets=widgets, new_widget_id=new_widget_id)

    @page.route("/clr/donations/<widget_id>/edit")
    @requires_level(1500)
    def clr_donations_edit(widget_id, **options):
        redis = RedisManager.get()
        widget = redis.hget("{streamer}:clr:donations".format(streamer=StreamHelper.get_streamer()), widget_id)
        new = False
        if widget is None:
            widget = {}
            new = True
        else:
            widget = json.loads(widget)

        return render_template(
            "admin/clr/donations/edit.html", widget_id=widget_id, widget_data=json.dumps(widget), new=new
        )
