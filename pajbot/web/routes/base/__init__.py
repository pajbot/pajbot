import pajbot.web.routes.base.decks
import pajbot.web.routes.base.commands
import pajbot.web.routes.base.home

def init(app):
    pajbot.web.routes.base.decks.init(app)
    pajbot.web.routes.base.commands.init(app)
    pajbot.web.routes.base.home.init(app)
