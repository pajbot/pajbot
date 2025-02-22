from __future__ import annotations

from typing import TYPE_CHECKING

import logging

from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import DBManager
from pajbot.models.command import Command, CommandExample
from pajbot.models.user import User
from pajbot.modules.base import BaseModule, ModuleSetting, ModuleType
from pajbot.modules.basic import BasicCommandsModule
from pajbot.response import AnyResponse, BanResponse, UnbanResponse, WhisperResponse

if TYPE_CHECKING:
    from pajbot.bot import Bot

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
    async def permaban_command(bot: Bot, source: User, message: str, **_) -> list[AnyResponse]:
        if not message:
            return []

        username = message.split(" ")[0]
        with DBManager.create_session_scope() as db_session:
            user = User.find_by_user_input(db_session, username)
            if not user:
                return WhisperResponse.one(source.id, "No user with that name found.")

            if user.banned:
                return WhisperResponse.one(source.id, "User is already permabanned.")

            user.banned = True
            log_msg = f"{user} has been permabanned"

            AdminLogManager.add_entry("Permaban added", source, log_msg)

            return [
                BanResponse(
                    user.id,
                    f"User has been added to the {bot.bot_user.login} banlist. Contact a moderator level 1000 or higher for unban.",
                ),
                WhisperResponse(source.id, log_msg),
            ]

    async def unpermaban_command(self, bot: Bot, source: User, message: str, **_) -> list[AnyResponse]:
        if not message:
            return []

        username = message.split(" ")[0]
        with DBManager.create_session_scope() as db_session:
            user = User.find_by_user_input(db_session, username)
            if not user:
                return WhisperResponse.one(source.id, "No user with that name found.")

            if user.banned is False:
                return WhisperResponse.one(source.id, "User is not permabanned.")

            user.banned = False
            log_msg = f"{user} is no longer permabanned"

            AdminLogManager.add_entry("Permaban remove", source, log_msg)

            if self.settings["unban_from_chat"] is True:
                bot.unban(user)

                if self.settings["enable_send_timeout"] is True:
                    bot.timeout(user, 1, self.settings["timeout_reason"].format(source=source))

            return [
                UnbanResponse(
                    user.id,
                ),
                WhisperResponse(source.id, log_msg),
            ]

    def load_commands(self, **_) -> None:
        self.commands["permaban"] = Command.raw_command(
            self.permaban_command,
            level=1000,
            description="Permanently ban a user. Every time the user types in chat, he will be permanently banned again",
            examples=[
                CommandExample(
                    None,
                    "Default usage",
                    chat="user:!permaban Karl_Kons\nbot>user:Karl_Kons has now been permabanned",
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
                    chat="user:!unpermaban Karl_Kons\nbot>user:Karl_Kons is no longer permabanned",
                    description="Remove permanent ban from Karl_Kons",
                ).parse()
            ],
        )
