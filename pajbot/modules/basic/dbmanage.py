import logging

import pajbot.models
from pajbot.modules import BaseModule
from pajbot.modules import ModuleType
from pajbot.modules.basic import BasicCommandsModule

log = logging.getLogger(__name__)


class DBManageModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'DB Managing commands'
    ENABLED_DEFAULT = True
    DESCRIPTION = '!reload/!commit'
    CATEGORY = 'Feature'
    PARENT_MODULE = BasicCommandsModule
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED

    def reload(self, **options):
        message = options['message']
        bot = options['bot']
        source = options['source']

        bot.whisper(source.username, 'Reloading things from DB...')

        if message and message in bot.reloadable:
            bot.reloadable[message].reload()
        else:
            bot.reload_all()

    def commit(self, **options):
        message = options['message']
        bot = options['bot']
        source = options['source']

        bot.whisper(source.username, 'Committing cached things to db...')

        if message and message in bot.commitable:
            bot.commitable[message].commit()
        else:
            bot.commit_all()

    def load_commands(self, **options):
        self.commands['reload'] = pajbot.models.command.Command.raw_command(self.reload,
                level=1000,
                description='Reload a bunch of data from the database')

        self.commands['commit'] = pajbot.models.command.Command.raw_command(self.commit,
                level=1000,
                description='Commit data from the bot to the database')
