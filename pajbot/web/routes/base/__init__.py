import pajbot.web.routes.base.decks
import pajbot.web.routes.base.commands

def init(app):
    pajbot.web.routes.base.decks.init(app)
    pajbot.web.routes.base.commands.init(app)
