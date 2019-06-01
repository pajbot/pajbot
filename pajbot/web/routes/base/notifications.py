from flask import render_template


def init(app):
    @app.route("/notifications/")
    def notifications():
        return render_template("notifications.html")
