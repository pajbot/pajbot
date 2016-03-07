import pajbot.web.routes.base.commands
import pajbot.web.routes.base.decks
import pajbot.web.routes.base.highlights
import pajbot.web.routes.base.home
import pajbot.web.routes.base.pleblist
import pajbot.web.routes.base.stats

def init(app):
    pajbot.web.routes.base.commands.init(app)
    pajbot.web.routes.base.decks.init(app)
    pajbot.web.routes.base.highlights.init(app)
    pajbot.web.routes.base.home.init(app)
    pajbot.web.routes.base.pleblist.init(app)
    pajbot.web.routes.base.stats.init(app)
