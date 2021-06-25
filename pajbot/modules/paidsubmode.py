import logging

from pajbot.models.command import Command
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class PaidSubmodeModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Paid Submode"
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
            constraints={"min_value": 1, "max_value": 1000000},
        ),
        ModuleSetting(
            key="suboff_cost",
            label="Point cost for turning sub mode off",
            type="number",
            required=True,
            placeholder="Point cost",
            default=1000,
            constraints={"min_value": 1, "max_value": 1000000},
        ),
    ]

    def paid_subon(self, bot, source, **rest):
        if bot.subs_only is True:
            bot.whisper(source, "Why would you try to enable subonly, if it's already enabled? FailFish")
            # Request to enable submode is ignored, but the return False ensures the user is refunded their points
            return False

        if bot.subs_only is False:
            _cost = self.settings["subon_cost"]

            # Test this a bit. Make sure twitch doesn't bug out
            bot.privmsg(".subscribers")
            bot.execute_delayed(0.2, bot.privmsg, ".subscribers")

            bot.whisper(source, f"You just used {_cost} points to put the chat into subscribers mode!")
            return True

    def paid_suboff(self, bot, source, **rest):
        if bot.subs_only is False:
            bot.whisper(source, "Why would you try to disable subonly, if it's not on in the first place? FailFish")
            # Request to disable submode is ignored, but the return False ensures the user is refunded their points
            return False

        if bot.subs_only is True:
            _cost = self.settings["suboff_cost"]

            # Test this a bit. Make sure twitch doesn't bug out
            bot.privmsg(".subscribersoff")
            bot.execute_delayed(0.2, bot.privmsg, ".subscribersoff")

            bot.whisper(source, f"You just used {_cost} points to put the chat into subscribers mode!")
            return True

    def load_commands(self, **options):
        self.commands[
            self.settings["subon_command_name"].lower().replace("!", "").replace(" ", "")
        ] = Command.raw_command(self.paid_subon, cost=self.settings["subon_cost"])
        self.commands[
            self.settings["suboff_command_name"].lower().replace("!", "").replace(" ", "")
        ] = Command.raw_command(self.paid_suboff, cost=self.settings["suboff_cost"])
