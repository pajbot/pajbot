import oldlib.routes.admin.banphrases
import oldlib.routes.admin.commands
import oldlib.routes.admin.home
import oldlib.routes.admin.links
import oldlib.routes.admin.moderators
import oldlib.routes.admin.modules
import oldlib.routes.admin.playsounds
import oldlib.routes.admin.streamer
import oldlib.routes.admin.timers

from flask import Blueprint


def init(app) -> None:
    page = Blueprint("admin", __name__, url_prefix="/admin")

    oldlib.routes.admin.banphrases.init(page)
    oldlib.routes.admin.commands.init(page)
    oldlib.routes.admin.home.init(page)
    oldlib.routes.admin.links.init(page)
    oldlib.routes.admin.moderators.init(page)
    oldlib.routes.admin.modules.init(page)
    oldlib.routes.admin.playsounds.init(page)
    oldlib.routes.admin.streamer.init(page)
    oldlib.routes.admin.timers.init(page)

    app.register_blueprint(page)
