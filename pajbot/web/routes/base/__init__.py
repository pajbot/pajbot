import pajbot.web.routes.base.commands
import pajbot.web.routes.base.contact
import pajbot.web.routes.base.decks
import pajbot.web.routes.base.home
import pajbot.web.routes.base.login
import pajbot.web.routes.base.playsounds
import pajbot.web.routes.base.pleblist
import pajbot.web.routes.base.points
import pajbot.web.routes.base.stats
import pajbot.web.routes.base.user


def init(app):
    pajbot.web.routes.base.commands.init(app)
    pajbot.web.routes.base.contact.init(app)
    pajbot.web.routes.base.decks.init(app)
    pajbot.web.routes.base.home.init(app)
    pajbot.web.routes.base.login.init(app)
    pajbot.web.routes.base.pleblist.init(app)
    pajbot.web.routes.base.points.init(app)
    pajbot.web.routes.base.stats.init(app)
    pajbot.web.routes.base.user.init(app)
    pajbot.web.routes.base.playsounds.init(app)
