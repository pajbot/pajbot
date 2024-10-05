from pajbot.managers.db import DBManager
from pajbot.models.playsound import Playsound
from pajbot.modules import PlaysoundModule

from flask import render_template


def init(app):
    @app.route("/playsounds")
    def user_playsounds():
        with DBManager.create_session_scope() as session:
            playsounds = session.query(Playsound).filter(Playsound.enabled).order_by(Playsound.name).all()

            return render_template(
                "playsounds.html",
                playsounds=playsounds,
                module_settings=PlaysoundModule.module_settings(),
                playsounds_enabled=PlaysoundModule.is_enabled(),
            )
