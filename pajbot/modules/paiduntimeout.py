import logging

from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class PaidUntimeoutModule(BaseModule):

    ID = "paiduntimeout"
    NAME = "Paid Untimeout"
    DESCRIPTION = "Allows users to unban themself with points"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="untimeout_enable",
            label="Enable untimeout command! (only remove timeouts, not permanent bans)",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="untimeout_command_name",
            label="Command name (i.e. untimeout)",
            type="text",
            required=True,
            placeholder="Command name (no !)",
            default="untimeout",
            constraints={"min_str_len": 2, "max_str_len": 15},
        ),
        ModuleSetting(
            key="untimeout_cost",
            label="Point cost",
            type="number",
            required=True,
            placeholder="Point cost",
            default=400,
            constraints={"min_value": 0, "max_value": 10000},
        ),
        ModuleSetting(
            key="unban_enable",
            label="Enable unban command! (removes timeouts and permanent bans)",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="unban_command_name",
            label="Command name (i.e. unban)",
            type="text",
            required=True,
            placeholder="Command name (no !)",
            default="unban",
            constraints={"min_str_len": 2, "max_str_len": 15},
        ),
        ModuleSetting(
            key="unban_cost",
            label="Point cost",
            type="number",
            required=True,
            placeholder="Point cost",
            default=1000,
            constraints={"min_value": 0, "max_value": 10000},
        ),
    ]

    @staticmethod
    def untimeout_source(**options):
        bot = options["bot"]
        source = options["source"]

        bot.privmsg(".timeout {0} 1".format(source.username))
        bot.whisper(source.username, "You have been unbanned.")
        source.timed_out = False

    @staticmethod
    def unban_source(**options):
        bot = options["bot"]
        source = options["source"]

        bot.privmsg(".unban {0}".format(source.username))
        bot.whisper(source.username, "You have been unbanned.")
        source.timed_out = False

    def load_commands(self, **options):
        if self.settings["untimeout_enable"]:
            self.commands[
                self.settings["untimeout_command_name"].lower().replace("!", "").replace(" ", "")
            ] = Command.raw_command(
                self.untimeout_source,
                cost=self.settings["untimeout_cost"],
                delay_all=0,
                delay_user=15,
                can_execute_with_whisper=True,
                description="Timed out for no apparent reason? Untimeout yourself using points!",
                examples=[
                    CommandExample(
                        None,
                        "Untimeout yourself for {0} points".format(self.settings["untimeout_cost"]),
                        chat="user>bot:!{0}\n"
                        "bot>user: You have been unbanned.".format(self.settings["untimeout_command_name"]),
                        description="",
                    ).parse()
                ],
            )
        if self.settings["unban_enable"]:
            self.commands[
                self.settings["unban_command_name"].lower().replace("!", "").replace(" ", "")
            ] = Command.raw_command(
                self.unban_source,
                cost=self.settings["unban_cost"],
                delay_all=0,
                delay_user=15,
                can_execute_with_whisper=True,
                description="Banned for no apparent reason? Unban yourself using points!",
                examples=[
                    CommandExample(
                        None,
                        "Unban yourself for {0} points".format(self.settings["unban_cost"]),
                        chat="user>bot:!{0}\n"
                        "bot>user: You have been unbanned.".format(self.settings["unban_command_name"]),
                        description="",
                    ).parse()
                ],
            )
