import pajweb.routes.api.banphrases
import pajweb.routes.api.commands
import pajweb.routes.api.common
import pajweb.routes.api.modules
import pajweb.routes.api.playsound
import pajweb.routes.api.social
import pajweb.routes.api.timers
import pajweb.routes.api.users

from flask import Blueprint


def init(app) -> None:
    # Initialize the v1 api
    # /api/v1
    bp = Blueprint("api", __name__, url_prefix="/api/v1")

    # Initialize any common settings and routes
    pajweb.routes.api.common.init(bp)

    # /users
    pajweb.routes.api.users.init(bp)

    # /commands
    pajweb.routes.api.commands.init(bp)

    # /social
    pajweb.routes.api.social.init(bp)

    # /timers
    pajweb.routes.api.timers.init(bp)

    # /banphrases
    pajweb.routes.api.banphrases.init(bp)

    # /modules
    pajweb.routes.api.modules.init(bp)

    # /playsound/:name
    # /playsound/:name/play
    pajweb.routes.api.playsound.init(bp)

    app.register_blueprint(bp)
