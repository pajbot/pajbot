import json

from flask import render_template

from pajbot.managers.db import DBManager
from pajbot.models.module import Module
from pajbot.models.playsound import Playsound
from pajbot.modules import PlaysoundModule


def init(app):
    @app.route('/playsounds/')
    def user_playsounds():
        with DBManager.create_session_scope() as session:
            playsounds = session.query(Playsound).filter(Playsound.enabled).all()
            playsound_module = session.query(Module).filter(Module.id == PlaysoundModule.ID).one()
            if playsound_module.settings is None:
                settings = dict(((setting.key, setting.default) for setting in PlaysoundModule.SETTINGS))
            else:
                settings = json.loads(playsound_module.settings)

            return render_template('playsounds.html', playsounds=playsounds, module_settings=settings,
                                   playsounds_enabled=playsound_module.enabled)
