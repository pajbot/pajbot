import logging

from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import DBManager
from pajbot.models.command import Command, CommandExample
from pajbot.models.user import User
from pajbot.modules import BaseModule, ModuleSetting, ModuleType
from pajbot.modules.basic import BasicCommandsModule

log = logging.getLogger(__name__)


class PermabanModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Permaban"
    DESCRIPTION = "Permabans a user (re-bans them if unbanned by a mod)"
    CATEGORY = "Moderation"
    ENABLED_DEFAULT = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED
    PARENT_MODULE = BasicCommandsModule
    SETTINGS = [
        ModuleSetting(
            key="unban_from_chat",
            label="Unban the user from chat when the unpermaban command is used",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="enable_send_timeout",
            label="Timeout the user for one second to note the unban reason in the mod logs",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="timeout_reason",
            label="Timeout Reason | Available arguments: {source}",
            type="text",
            required=False,
            placeholder="",
            default="Un-permabanned by {source}",
            constraints={},
        ),
    ]

    @staticmethod
    def permaban_command(bot, source, message, **rest) -> bool:
        if not message:
            return False

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
            bot.ban(
                user,
                reason=f"User has been added to the {bot.bot_user.login} banlist. Contact a moderator level 1000 or higher for unban.",
            )
            log_msg = f"{user} has been permabanned"
            bot.whisper(source, log_msg)

            AdminLogManager.add_entry("Permaban added", source, log_msg)

        return True

    def unpermaban_command(self, bot, source, message, **rest) -> bool:
        if not message:
            return False

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

            if self.settings["unban_from_chat"] is True:
                bot.unban(user)

                if self.settings["enable_send_timeout"] is True:
                    bot.timeout(user, 1, self.settings["timeout_reason"].format(source=source), once=True)

        return True

    def load_commands(self, **options) -> None:
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
