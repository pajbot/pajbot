import pajbot.web.routes.api.banphrases
import pajbot.web.routes.api.commands
import pajbot.web.routes.api.common
import pajbot.web.routes.api.modules
import pajbot.web.routes.api.playsound
import pajbot.web.routes.api.social
import pajbot.web.routes.api.timers
import pajbot.web.routes.api.twitter
import pajbot.web.routes.api.users

from flask import Blueprint


def init(app) -> None:
    # Initialize the v1 api
    # /api/v1
    bp = Blueprint("api", __name__, url_prefix="/api/v1")

    # Initialize any common settings and routes
    pajbot.web.routes.api.common.init(bp)

    # /users
    pajbot.web.routes.api.users.init(bp)

    # /twitter
    pajbot.web.routes.api.twitter.init(bp)

    # /commands
    pajbot.web.routes.api.commands.init(bp)

    # /social
    pajbot.web.routes.api.social.init(bp)

    # /timers
    pajbot.web.routes.api.timers.init(bp)

    # /banphrases
    pajbot.web.routes.api.banphrases.init(bp)

    # /modules
    pajbot.web.routes.api.modules.init(bp)

    # /playsound/:name
    # /playsound/:name/play
    pajbot.web.routes.api.playsound.init(bp)

    app.register_blueprint(bp)
