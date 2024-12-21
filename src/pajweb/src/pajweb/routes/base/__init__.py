import pajweb.routes.base.commands
import pajweb.routes.base.contact
import pajweb.routes.base.decks
import pajweb.routes.base.home
import pajweb.routes.base.login
import pajweb.routes.base.playsounds
import pajweb.routes.base.points
import pajweb.routes.base.stats
import pajweb.routes.base.user


def init(app):
    pajweb.routes.base.commands.init(app)
    pajweb.routes.base.contact.init(app)
    pajweb.routes.base.decks.init(app)
    pajweb.routes.base.home.init(app)
    pajweb.routes.base.login.init(app)
    pajweb.routes.base.points.init(app)
    pajweb.routes.base.stats.init(app)
    pajweb.routes.base.user.init(app)
    pajweb.routes.base.playsounds.init(app)
