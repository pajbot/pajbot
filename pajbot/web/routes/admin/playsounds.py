import json

from flask import render_template

from pajbot.managers.db import DBManager
from pajbot.models.module import Module
from pajbot.models.playsound import Playsound
from pajbot.modules import PlaysoundModule
from pajbot.web.utils import requires_level


def init(page):
    @page.route('/playsounds/')
    @requires_level(500)
    def playsounds(**options):
        with DBManager.create_session_scope() as session:
            playsounds = session.query(Playsound).filter(Playsound.enabled).all()
            playsound_module = session.query(Module).filter(Module.id == PlaysoundModule.ID).one()
            settings = json.loads(playsound_module.settings)

            return render_template('admin/playsounds.html', playsounds=playsounds, module_settings=settings,
                                   playsounds_enabled=playsound_module.enabled)
