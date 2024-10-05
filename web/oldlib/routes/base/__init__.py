import oldlib.routes.base.commands
import oldlib.routes.base.contact
import oldlib.routes.base.decks
import oldlib.routes.base.home
import oldlib.routes.base.login
import oldlib.routes.base.playsounds
import oldlib.routes.base.points
import oldlib.routes.base.stats
import oldlib.routes.base.user


def init(app):
    oldlib.routes.base.commands.init(app)
    oldlib.routes.base.contact.init(app)
    oldlib.routes.base.decks.init(app)
    oldlib.routes.base.home.init(app)
    oldlib.routes.base.login.init(app)
    oldlib.routes.base.points.init(app)
    oldlib.routes.base.stats.init(app)
    oldlib.routes.base.user.init(app)
    oldlib.routes.base.playsounds.init(app)
