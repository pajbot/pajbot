from flask import render_template

import logging

log = logging.getLogger(__name__)


def init(app):
    try:
        maintainer = {
            "name": app.bot_config["maintainer"]["name"],
            "contact_string": app.bot_config["maintainer"]["contact_string"],
        }
    except KeyError:
        log.warn(
            "Missing name and/or contact_string in config file, no direct contact info will be shown on the /contact page. See example config file"
        )
        maintainer = None

    @app.route("/contact")
    def contact():
        return render_template("contact.html", maintainer=maintainer)
