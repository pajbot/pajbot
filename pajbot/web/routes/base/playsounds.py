from flask import render_template

from pajbot.managers.db import DBManager
from pajbot.models.module import Module
from pajbot.models.playsound import Playsound
from pajbot.modules import PlaysoundModule


def init(app):
    @app.route("/playsounds/")
    def user_playsounds():
        with DBManager.create_session_scope() as session:
            playsounds = session.query(Playsound).filter(Playsound.enabled).order_by(Playsound.name).all()
            playsound_module = session.query(Module).filter(Module.id == PlaysoundModule.ID).one_or_none()

            enabled = False
            if playsound_module is not None:
                enabled = playsound_module.enabled

            return render_template(
                "playsounds.html",
                playsounds=playsounds,
                module_settings=PlaysoundModule.module_settings(),
                playsounds_enabled=enabled,
            )
