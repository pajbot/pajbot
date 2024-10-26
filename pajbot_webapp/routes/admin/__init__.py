import pajbot_webapp.routes.admin.banphrases
import pajbot_webapp.routes.admin.commands
import pajbot_webapp.routes.admin.home
import pajbot_webapp.routes.admin.links
import pajbot_webapp.routes.admin.moderators
import pajbot_webapp.routes.admin.modules
import pajbot_webapp.routes.admin.playsounds
import pajbot_webapp.routes.admin.streamer
import pajbot_webapp.routes.admin.timers

from flask import Blueprint


def init(app) -> None:
    page = Blueprint("admin", __name__, url_prefix="/admin")

    pajbot_webapp.routes.admin.banphrases.init(page)
    pajbot_webapp.routes.admin.commands.init(page)
    pajbot_webapp.routes.admin.home.init(page)
    pajbot_webapp.routes.admin.links.init(page)
    pajbot_webapp.routes.admin.moderators.init(page)
    pajbot_webapp.routes.admin.modules.init(page)
    pajbot_webapp.routes.admin.playsounds.init(page)
    pajbot_webapp.routes.admin.streamer.init(page)
    pajbot_webapp.routes.admin.timers.init(page)

    app.register_blueprint(page)
