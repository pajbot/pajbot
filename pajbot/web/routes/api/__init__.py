from flask_restful import Api

import pajbot.web.routes.api.banphrases
import pajbot.web.routes.api.clr
import pajbot.web.routes.api.commands
import pajbot.web.routes.api.common
import pajbot.web.routes.api.email
import pajbot.web.routes.api.modules
import pajbot.web.routes.api.pleblist
import pajbot.web.routes.api.social
import pajbot.web.routes.api.streamtip
import pajbot.web.routes.api.streamelements
import pajbot.web.routes.api.timers
import pajbot.web.routes.api.streamlabs
import pajbot.web.routes.api.twitter
import pajbot.web.routes.api.users


def init(app):
    # Initialize the v1 api
    # /api/v1
    api = Api(app, prefix='/api/v1', catch_all_404s=True)

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

    # /streamtip
    pajbot.web.routes.api.streamtip.init(api)

    # /streamlabs
    pajbot.web.routes.api.streamlabs.init(api)

    # /clr
    pajbot.web.routes.api.clr.init(api)

    # /email
    pajbot.web.routes.api.email.init(api)

    # /social
    pajbot.web.routes.api.social.init(api)

    # /timers
    pajbot.web.routes.api.timers.init(api)

    # /banphrases
    pajbot.web.routes.api.banphrases.init(api)

    # /modules
    pajbot.web.routes.api.modules.init(api)

    # /streamelements
    pajbot.web.routes.api.streamelements.init(api)
