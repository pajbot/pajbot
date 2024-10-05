import oldlib.routes.api.banphrases
import oldlib.routes.api.commands
import oldlib.routes.api.common
import oldlib.routes.api.modules
import oldlib.routes.api.playsound
import oldlib.routes.api.social
import oldlib.routes.api.timers
import oldlib.routes.api.users

from flask import Blueprint


def init(app) -> None:
    # Initialize the v1 api
    # /api/v1
    bp = Blueprint("api", __name__, url_prefix="/api/v1")

    # Initialize any common settings and routes
    oldlib.routes.api.common.init(bp)

    # /users
    oldlib.routes.api.users.init(bp)

    # /commands
    oldlib.routes.api.commands.init(bp)

    # /social
    oldlib.routes.api.social.init(bp)

    # /timers
    oldlib.routes.api.timers.init(bp)

    # /banphrases
    oldlib.routes.api.banphrases.init(bp)

    # /modules
    oldlib.routes.api.modules.init(bp)

    # /playsound/:name
    # /playsound/:name/play
    oldlib.routes.api.playsound.init(bp)

    app.register_blueprint(bp)
