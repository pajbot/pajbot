import pajbot.web.routes.api.banphrases
import pajbot.web.routes.api.commands
import pajbot.web.routes.api.common
import pajbot.web.routes.api.modules
import pajbot.web.routes.api.playsound
import pajbot.web.routes.api.pleblist
import pajbot.web.routes.api.social
import pajbot.web.routes.api.timers
import pajbot.web.routes.api.twitter
import pajbot.web.routes.api.users

from flask_restful import Api


def init(app):
    # Initialize the v1 api
    # /api/v1
    api = Api(app, prefix="/api/v1", catch_all_404s=False)

    # Initialize any common settings and routes
    pajbot.web.routes.api.common.init(api)

    # /users
    pajbot.web.routes.api.users.init(api)

    # /twitter
    pajbot.web.routes.api.twitter.init(api)

    # /commands
    pajbot.web.routes.api.commands.init(api)

    # /pleblist
    pajbot.web.routes.api.pleblist.init(api)

    # /social
    pajbot.web.routes.api.social.init(api)

    # /timers
    pajbot.web.routes.api.timers.init(api)

    # /banphrases
    pajbot.web.routes.api.banphrases.init(api)

    # /modules
    pajbot.web.routes.api.modules.init(api)

    # /playsound/:name
    # /playsound/:name/play
    pajbot.web.routes.api.playsound.init(api)
