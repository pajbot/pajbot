import logging

from pajbot.managers.db import DBManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.models.user import User
from pajbot.modules import BaseModule
from pajbot.modules import ModuleType
from pajbot.modules.basic import BasicCommandsModule

log = logging.getLogger(__name__)


class IgnoreModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "!ignore/!unignore"
    DESCRIPTION = "Ignore all commands from a user"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED
    PARENT_MODULE = BasicCommandsModule

    @staticmethod
    def ignore_command(bot, source, message, **rest):
        if not message:
            return False

        with DBManager.create_session_scope() as db_session:
            username = message.split(" ")[0]
            user = User.find_by_user_input(db_session, username)

            if user == source:
                bot.whisper(source, "You cannot ignore yourself")
                return False

        with DBManager.create_session_scope() as db_session:
            user = User.find_by_user_input(db_session, username)
            if user is None:
                bot.whisper(source, "No user with that name found.")
                return False

            if user.ignored:
                bot.whisper(source, "User is already ignored.")
                return False

            user.ignored = True
            bot.whisper(source, f"Now ignoring {user}")

    @staticmethod
    def unignore_command(bot, source, message, **rest):
        if not message:
            return

        username = message.split(" ")[0]
        with DBManager.create_session_scope() as db_session:
            user = User.find_by_user_input(db_session, username)
            if not user:
                bot.whisper(source, "No user with that name found.")
                return False

            if user.ignored is False:
                bot.whisper(source, "User is not ignored.")
                return False

            user.ignored = False
            bot.whisper(source, f"No longer ignoring {user}")

    def load_commands(self, **options):
        self.commands["ignore"] = Command.raw_command(
            self.ignore_command,
            level=1000,
            description="Ignore a user, which means he can't run any commands",
            examples=[
                CommandExample(
                    None,
                    "Default usage",
                    chat="user:!ignore Karl_Kons\n" "bot>user:Now ignoring Karl_Kons",
                    description="Ignore user Karl_Kons",
                ).parse()
            ],
        )

        self.commands["unignore"] = Command.raw_command(
            self.unignore_command,
            level=1000,
            description="Unignore a user",
            examples=[
                CommandExample(
                    None,
                    "Default usage",
                    chat="user:!unignore Karl_Kons\n" "bot>user:No longer ignoring Karl_Kons",
                    description="Unignore user Karl_Kons",
                ).parse()
            ],
        )
