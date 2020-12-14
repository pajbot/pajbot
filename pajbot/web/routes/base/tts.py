from flask import render_template

import logging

log = logging.getLogger(__name__)


def init(app):
    @app.route("/tts")
    def tts():
        return render_template("tts.html")
