from flask import render_template


def init(app):
    @app.route("/contact")
    def contact():
        return render_template("contact.html")
