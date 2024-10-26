import pajbot_webapp.routes.api.banphrases
import pajbot_webapp.routes.api.commands
import pajbot_webapp.routes.api.common
import pajbot_webapp.routes.api.modules
import pajbot_webapp.routes.api.playsound
import pajbot_webapp.routes.api.social
import pajbot_webapp.routes.api.timers
import pajbot_webapp.routes.api.users

from flask import Blueprint


def init(app) -> None:
    # Initialize the v1 api
    # /api/v1
    bp = Blueprint("api", __name__, url_prefix="/api/v1")

    # Initialize any common settings and routes
    pajbot_webapp.routes.api.common.init(bp)

    # /users
    pajbot_webapp.routes.api.users.init(bp)

    # /commands
    pajbot_webapp.routes.api.commands.init(bp)

    # /social
    pajbot_webapp.routes.api.social.init(bp)

    # /timers
    pajbot_webapp.routes.api.timers.init(bp)

    # /banphrases
    pajbot_webapp.routes.api.banphrases.init(bp)

    # /modules
    pajbot_webapp.routes.api.modules.init(bp)

    # /playsound/:name
    # /playsound/:name/play
    pajbot_webapp.routes.api.playsound.init(bp)

    app.register_blueprint(bp)
