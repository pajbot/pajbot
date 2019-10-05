import logging

from flask import render_template
from flask import request

from pajbot.web.utils import format_tb

log = logging.getLogger(__name__)


def init(app, config):
    slack = None
    try:
        import slackweb

        if "slack" in config and "webhook" in config["slack"]:
            slack = slackweb.Slack(url=config["slack"]["webhook"])
    except:
        pass

    def slack_alert(message):
        try:
            if slack:
                slack.notify(text=message)
        except:
            pass

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_errors(e):
        slack_alert(f"500 error on {request.url}:\n{e}")
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(Exception)
    def all_exception_handler(error):
        log.exception("Unhandled exception")
        slack_alert(f"*Unhandled exception* on {request.url}\n{error}\n{format_tb(error.__traceback__)}\n\n")
        return render_template("errors/500_unhandled.html"), 500
