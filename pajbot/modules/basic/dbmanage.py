import logging

from pajbot.models.command import Command
from pajbot.modules import BaseModule
from pajbot.modules import ModuleType
from pajbot.modules.basic import BasicCommandsModule

log = logging.getLogger(__name__)


class DBManageModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "DB Managing commands"
    ENABLED_DEFAULT = True
    DESCRIPTION = "!reload/!commit"
    CATEGORY = "Feature"
    PARENT_MODULE = BasicCommandsModule
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED

    @staticmethod
    def commit(bot, source, message, **rest):
        bot.whisper(source, "Committing cached things to db...")

        if message and message in bot.commitable:
            bot.commitable[message].commit()
        else:
            bot.commit_all()

    def load_commands(self, **options):
        self.commands["commit"] = Command.raw_command(
            self.commit, level=1000, description="Commit data from the bot to the database"
        )
