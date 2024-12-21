import pajweb.routes.admin.banphrases
import pajweb.routes.admin.commands
import pajweb.routes.admin.home
import pajweb.routes.admin.links
import pajweb.routes.admin.moderators
import pajweb.routes.admin.modules
import pajweb.routes.admin.playsounds
import pajweb.routes.admin.streamer
import pajweb.routes.admin.timers

from flask import Blueprint


def init(app) -> None:
    page = Blueprint("admin", __name__, url_prefix="/admin")

    pajweb.routes.admin.banphrases.init(page)
    pajweb.routes.admin.commands.init(page)
    pajweb.routes.admin.home.init(page)
    pajweb.routes.admin.links.init(page)
    pajweb.routes.admin.moderators.init(page)
    pajweb.routes.admin.modules.init(page)
    pajweb.routes.admin.playsounds.init(page)
    pajweb.routes.admin.streamer.init(page)
    pajweb.routes.admin.timers.init(page)

    app.register_blueprint(page)
