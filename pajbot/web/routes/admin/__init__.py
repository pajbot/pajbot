from flask import Blueprint

import pajbot.web.routes.admin.banphrases
import pajbot.web.routes.admin.commands
import pajbot.web.routes.admin.home
import pajbot.web.routes.admin.links
import pajbot.web.routes.admin.moderators
import pajbot.web.routes.admin.modules
import pajbot.web.routes.admin.playsounds
import pajbot.web.routes.admin.predictions
import pajbot.web.routes.admin.streamer
import pajbot.web.routes.admin.timers


def init(app):
    page = Blueprint("admin", __name__, url_prefix="/admin")

    pajbot.web.routes.admin.banphrases.init(page)
    pajbot.web.routes.admin.commands.init(page)
    pajbot.web.routes.admin.home.init(page)
    pajbot.web.routes.admin.links.init(page)
    pajbot.web.routes.admin.moderators.init(page)
    pajbot.web.routes.admin.modules.init(page)
    pajbot.web.routes.admin.playsounds.init(page)
    pajbot.web.routes.admin.predictions.init(page)
    pajbot.web.routes.admin.streamer.init(page)
    pajbot.web.routes.admin.timers.init(page)

    app.register_blueprint(page)
