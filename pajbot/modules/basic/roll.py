import logging, random

from pajbot.models.command import Command, CommandExample
from pajbot.modules import BaseModule, ModuleSetting
from pajbot.modules.basic import BasicCommandsModule

log = logging.getLogger(__name__)


class RollModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Roll"
    DESCRIPTION = "Allows users to roll a random number, which can also be used as timeout times"
    CATEGORY = "Feature"
    PARENT_MODULE = BasicCommandsModule
    SETTINGS = [
        ModuleSetting(
            key="subscribers_only",
            label="Only allow subscribers to use the !roll command.",
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
            key="low_value",
            label="Lowest number to roll from",
            type="number",
            required=True,
            placeholder="1",
            default=1,
            constraints={"min_value": 0},
        ),
        ModuleSetting(
            key="high_value",
            label="Highest number to roll to",
            type="number",
            required=True,
            placeholder="100",
            default=100,
            constraints={"min_value": 1},
        ),
        ModuleSetting(
            key="enable_timeouts",
            label="Enable the values rolled to be used as timeout values",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="announce_rolls",
            label="Announce in chat what number a user rolls when timeouts are enabled",
            type="boolean",
            required=True,
            default=True,
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
            label="Additional text to say when the user rolls a 0. Timeouts must be enabled.",
            type="text",
            required=False,
            placeholder="You're safe! For now... PRChase",
            default="You're safe! For now... PRChase",
            constraints={"max_str_len": 100},
        ),
    ]

    def load_commands(self, **options):
        self.commands["roll"] = Command.raw_command(
            self.roll,
            sub_only=self.settings["subscribers_only"],
            delay_all=self.settings["global_cd"],
            delay_user=self.settings["user_cd"],
            level=self.settings["level"],
            command="roll",
            examples=[
                CommandExample(
                    None,
                    "Roll a random number",
                    chat="user:!roll\n" "bot:@pajlada You rolled a 9!",
                    description="",
                ).parse(),
            ],
        )

    # We're converting timeout times to seconds in order to avoid having to specify the unit to Twitch
    def seconds_conversion(self, rolled_value):
        if rolled_value != 0:
            if self.settings["timeout_unit"] == "Seconds":
                return rolled_value
            elif self.settings["timeout_unit"] == "Minutes":
                return rolled_value * 60
            elif self.settings["timeout_unit"] == "Hours":
                return rolled_value * 3600
            elif self.settings["timeout_unit"] == "Days":
                return rolled_value * 86400
            elif self.settings["timeout_unit"] == "Weeks":
                return rolled_value * 604800
        else:
            return True

    def roll(self, event, source, **rest):
        if self.settings["subscribers_only"] and not source.subscriber:
            return True

        rolled_value = random.randint(self.settings["low_value"], self.settings["high_value"])

        if self.settings["enable_timeouts"] is True:
            if rolled_value == 0 and self.settings["zero_response"] != "":
                self.bot.send_message_to_user(
                    source, f"You rolled a {rolled_value}! {self.settings['zero_response']}", event, method="reply"
                )
            else:
                timeout_length = self.seconds_conversion(rolled_value)
                # Check if timeout value is over Twitch's maximum
                if timeout_length > 1209600:
                    timeout_length = 1209600

                self.bot.timeout(source, timeout_length, f"You rolled a {rolled_value}!")

                if self.settings["announce_rolls"] is True:
                    self.bot.send_message_to_user(source, f"You rolled a {rolled_value}!", event, method="reply")
        else:
            self.bot.send_message_to_user(source, f"You rolled a {rolled_value}!", event, method="reply")
