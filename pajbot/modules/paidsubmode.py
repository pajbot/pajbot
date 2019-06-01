import logging

from pajbot.models.command import Command
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class PaidSubmodeModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Paid SubOn/SubOff"
    DESCRIPTION = "Allows user to toggle subscribers mode on and off using points."
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="subon_command_name",
            label="Command name for turning sub mode on (i.e. $subon)",
            type="text",
            required=True,
            placeholder="Command name (no !)",
            default="$subon",
            constraints={"min_str_len": 2, "max_str_len": 15},
        ),
        ModuleSetting(
            key="suboff_command_name",
            label="Command name for turning sub mode off (i.e. $suboff)",
            type="text",
            required=True,
            placeholder="Command name (no !)",
            default="$suboff",
            constraints={"min_str_len": 2, "max_str_len": 15},
        ),
        ModuleSetting(
            key="subon_cost",
            label="Point cost for turning sub mode on",
            type="number",
            required=True,
            placeholder="Point cost",
            default=1000,
            constraints={"min_value": 1, "max_value": 30000},
        ),
        ModuleSetting(
            key="suboff_cost",
            label="Point cost for turning sub mode off",
            type="number",
            required=True,
            placeholder="Point cost",
            default=1000,
            constraints={"min_value": 1, "max_value": 30000},
        ),
    ]

    def paid_subon(self, **options):
        bot = options["bot"]
        source = options["source"]

        _cost = self.settings["subon_cost"]

        # Test this a bit. Make sure twitch doesn't bug out
        bot.privmsg(".subscribers")
        bot.execute_delayed(0.2, bot.privmsg, (".subscribers",))

        bot.whisper(source.username, "You just used {} points to put the chat into subscribers mode!".format(_cost))

    def paid_suboff(self, **options):
        bot = options["bot"]
        source = options["source"]

        _cost = self.settings["suboff_cost"]

        # Test this a bit. Make sure twitch doesn't bug out
        bot.privmsg(".subscribersoff")
        bot.execute_delayed(0.2, bot.privmsg, (".subscribersoff",))

        bot.whisper(source.username, "You just used {} points to put the chat into subscribers mode!".format(_cost))

    def load_commands(self, **options):
        self.commands[
            self.settings["subon_command_name"].lower().replace("!", "").replace(" ", "")
        ] = Command.raw_command(self.paid_subon, cost=self.settings["subon_cost"])
        self.commands[
            self.settings["suboff_command_name"].lower().replace("!", "").replace(" ", "")
        ] = Command.raw_command(self.paid_suboff, cost=self.settings["suboff_cost"])
