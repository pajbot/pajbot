import pajbot_webapp.routes.base.commands
import pajbot_webapp.routes.base.contact
import pajbot_webapp.routes.base.decks
import pajbot_webapp.routes.base.home
import pajbot_webapp.routes.base.login
import pajbot_webapp.routes.base.playsounds
import pajbot_webapp.routes.base.points
import pajbot_webapp.routes.base.stats
import pajbot_webapp.routes.base.user


def init(app):
    pajbot_webapp.routes.base.commands.init(app)
    pajbot_webapp.routes.base.contact.init(app)
    pajbot_webapp.routes.base.decks.init(app)
    pajbot_webapp.routes.base.home.init(app)
    pajbot_webapp.routes.base.login.init(app)
    pajbot_webapp.routes.base.points.init(app)
    pajbot_webapp.routes.base.stats.init(app)
    pajbot_webapp.routes.base.user.init(app)
    pajbot_webapp.routes.base.playsounds.init(app)
