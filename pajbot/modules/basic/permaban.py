import logging

from pajbot.managers.adminlog import AdminLogManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
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
    def permaban_command(**options):
        message = options["message"]
        bot = options["bot"]
        source = options["source"]

        if message:
            username = message.split(" ")[0].strip().lower()
            with bot.users.get_user_context(username) as user:
                if user.banned:
                    bot.whisper(source.username, "User is already permabanned.")
                    return False

                user.banned = True
                message = message.lower()
                log_msg = "{} has been permabanned".format(user.username_raw)
                bot.whisper(source.username, log_msg)

                AdminLogManager.add_entry("Permaban added", source, log_msg)

    @staticmethod
    def unpermaban_command(**options):
        message = options["message"]
        bot = options["bot"]
        source = options["source"]

        if message:
            username = message.split(" ")[0].strip().lower()
            with bot.users.find_context(username) as user:
                if not user:
                    bot.whisper(source.username, "No user with that name found.")
                    return False

                if user.banned is False:
                    bot.whisper(source.username, "User is not permabanned.")
                    return False

                user.banned = False
                message = message.lower()
                log_msg = "{} is no longer permabanned".format(user.username_raw)
                bot.whisper(source.username, log_msg)

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
