from __future__ import annotations

from typing import TYPE_CHECKING, Any

import logging
import random

from pajbot.models.command import Command, CommandExample
from pajbot.modules import BaseModule, ModuleSetting
from pajbot.modules.basic import BasicCommandsModule

if TYPE_CHECKING:
    from pajbot.bot import Bot
    from pajbot.models.user import User

log = logging.getLogger(__name__)


class SelfTimeoutModule(BaseModule):
    ID = __name__.rsplit(".", maxsplit=1)[-1]
    NAME = "Self timeout"
    DESCRIPTION = "Allows users to timeout themselves based on a random duration."
    CATEGORY = "Feature"
    PARENT_MODULE = BasicCommandsModule
    SETTINGS = [
        ModuleSetting(
            key="subscribers_only",
            label="Only allow subscribers to use the !selftimeout command.",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="vip_only",
            label="Only allow VIPs to use the !selftimeout command.",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="global_cd",
            label="Global cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=5,
            constraints={"min_value": 0, "max_value": 120},
        ),
        ModuleSetting(
            key="user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=15,
            constraints={"min_value": 0, "max_value": 240},
        ),
        ModuleSetting(
            key="level",
            label="Level required to use the command",
            type="number",
            required=True,
            placeholder="",
            default=100,
            constraints={"min_value": 100, "max_value": 2000},
        ),
        ModuleSetting(
            key="command_name",
            label="Command name (e.g. selftimeout)",
            type="text",
            required=True,
            placeholder="Command name (no !)",
            default="selftimeout",
            constraints={"min_str_len": 1, "max_str_len": 15},
        ),
        ModuleSetting(
            key="low_value",
            label="Lowest number to select from",
            type="number",
            required=True,
            placeholder="0",
            default=0,
            constraints={"min_value": 0},
        ),
        ModuleSetting(
            key="high_value",
            label="Highest number to select to",
            type="number",
            required=True,
            placeholder="100",
            default=100,
            constraints={"min_value": 1},
        ),
        ModuleSetting(
            key="timeout_unit",
            label="Choose the timeout format to use. Maximum Twitch timeout limits are enforced.",
            type="options",
            required=False,
            default="Minutes",
            options=["Seconds", "Minutes", "Hours", "Days", "Weeks"],
        ),
        ModuleSetting(
            key="zero_response",
            label="Additional text to say when the user gets a 0. Text is disabled for moderator rolls.",
            type="text",
            required=False,
            placeholder="You're safe! For now... PRChase",
            default="You're safe! For now... PRChase",
            constraints={"max_str_len": 100},
        ),
    ]

    def load_commands(self, **options) -> None:
        self.commands[self.settings["command_name"].lower().replace("!", "").replace(" ", "")] = Command.raw_command(
            self.selftimeout,
            sub_only=self.settings["subscribers_only"],
            delay_all=self.settings["global_cd"],
            delay_user=self.settings["user_cd"],
            level=self.settings["level"],
            examples=[
                CommandExample(
                    None,
                    "Get timed out for a random duration",
                    chat="user:!selftimeout",
                    description="You don't get confirmation, only a timeout.",
                ).parse(),
            ],
        )

    # We're converting timeout times to seconds in order to avoid having to specify the unit to Twitch
    def seconds_conversion(self, random_value: int) -> int:
        if self.settings["timeout_unit"] == "Seconds":
            return random_value

        if self.settings["timeout_unit"] == "Minutes":
            return random_value * 60

        if self.settings["timeout_unit"] == "Hours":
            return random_value * 3600

        if self.settings["timeout_unit"] == "Days":
            return random_value * 86400

        if self.settings["timeout_unit"] == "Weeks":
            return random_value * 604800

        # Could raise an exception here instead too
        return 0

    def selftimeout(self, bot: Bot, source: User, event: Any, **rest) -> bool:
        if self.settings["subscribers_only"] and not source.subscriber:
            return True

        if self.settings["vip_only"] and not source.vip:
            return True

        if source.moderator is True:
            return True

        random_value = random.randint(self.settings["low_value"], self.settings["high_value"])
        standard_response = f"You got a {random_value}"

        if random_value == 0 and self.settings["zero_response"] != "":
            bot.send_message_to_user(
                source, f"{standard_response}. {self.settings['zero_response']}", event, method="reply"
            )
        else:
            timeout_length = self.seconds_conversion(random_value)

            # Check if timeout value is over Twitch's maximum
            timeout_length = min(timeout_length, 1209600)

            bot.timeout(source, timeout_length, f"{standard_response}!", once=True)

        return True
