import logging

from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import DBManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.models.user import User
from pajbot.modules import BaseModule
from pajbot.modules import ModuleType
from pajbot.modules.basic import BasicCommandsModule

log = logging.getLogger(__name__)


class PermabanModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "!permaban/!unpermaban"
    DESCRIPTION = "Permaban a user. (re-bans him if unbanned by mod)"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED
    PARENT_MODULE = BasicCommandsModule

    @staticmethod
    def permaban_command(bot, source, message, **rest):
        if not message:
            return

        username = message.split(" ")[0]
        with DBManager.create_session_scope() as db_session:
            user = User.find_by_user_input(db_session, username)
            if not user:
                bot.whisper(source, "No user with that name found.")
                return False

            if user.banned:
                bot.whisper(source, "User is already permabanned.")
                return False

            user.banned = True
            log_msg = f"{user} has been permabanned"
            bot.whisper(source, log_msg)

            AdminLogManager.add_entry("Permaban added", source, log_msg)

    @staticmethod
    def unpermaban_command(bot, source, message, **rest):
        if not message:
            return

        username = message.split(" ")[0]
        with DBManager.create_session_scope() as db_session:
            user = User.find_by_user_input(db_session, username)
            if not user:
                bot.whisper(source, "No user with that name found.")
                return False

            if user.banned is False:
                bot.whisper(source, "User is not permabanned.")
                return False

            user.banned = False
            log_msg = f"{user} is no longer permabanned"
            bot.whisper(source, log_msg)

            AdminLogManager.add_entry("Permaban remove", source, log_msg)

    def load_commands(self, **options):
        self.commands["permaban"] = Command.raw_command(
            self.permaban_command,
            level=1000,
            description="Permanently ban a user. Every time the user types in chat, he will be permanently banned again",
            examples=[
                CommandExample(
                    None,
                    "Default usage",
                    chat="user:!permaban Karl_Kons\n" "bot>user:Karl_Kons has now been permabanned",
                    description="Permanently ban Karl_Kons from the chat",
                ).parse()
            ],
        )

        self.commands["unpermaban"] = Command.raw_command(
            self.unpermaban_command,
            level=1000,
            description="Remove a permanent ban from a user",
            examples=[
                CommandExample(
                    None,
                    "Default usage",
                    chat="user:!unpermaban Karl_Kons\n" "bot>user:Karl_Kons is no longer permabanned",
                    description="Remove permanent ban from Karl_Kons",
                ).parse()
            ],
        )
