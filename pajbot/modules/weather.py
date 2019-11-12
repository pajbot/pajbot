import logging

import requests

from pajbot.models.command import Command
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class DarkSkyWeather(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Dark Sky Weather"
    DESCRIPTION = "Simple module for some weather commands - <a href="https://darksky.net/poweredby">Powered by Dark Sky</a> - Requires Dark Sky key in the bot config file"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="level",
            label="Level required to use the command (make sure people don't abuse this command)",
            type="number",
            required=True,
            placeholder="",
            default=250,
            constraints={"min_value": 100, "max_value": 2000},
        ),
        ModuleSetting(
            key="global_cd",
            label="Global cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=15,
            constraints={"min_value": 0, "max_value": 240},
        ),
        ModuleSetting(
            key="user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=30,
            constraints={"min_value": 0, "max_value": 240},
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)

        if bot:
            self.darksky_key = bot.config["main"].get("darksky", None)

        if not self.darksky_key:
            # XXX: Possibly notify user of misconfigured bot?
            return False

        try:
            log.debug('Querying darksky for input "%s"', message)

            query_parameters = {
                "key": self.darksky_key,
            }

            res = requests.get("https://api.darksky.net/forecast/", params=query_parameters)
            answer = res.json()["queryresult"]

            base_reply = f"{source}, "

            is_error = answer["error"]
            is_success = answer["success"]
            log.debug("Result status: error: %s, success: %s", is_error, is_success)

            if is_error:
                reply = base_reply + "your request errored FeelsBadMan"
                bot.send_message_to_user(source, reply, event, method="reply")
                return False

            if not is_success:
                log.debug(answer)
                reply = base_reply + "DarkSky didn't understand your request FeelsBadMan"

        except:
            log.exception("wolfram query errored")

    def load_commands(self, **options):
        self.commands["weather"] = Command.raw_command(
            delay_all=self.settings["global_cd"],
            delay_user=self.settings["user_cd"],
            level=self.settings["level"],
            description="Find the weather for a specified location",
            command="weather",
            examples=[],
        )
        self.commands["weather"] = self.commands["forecase"]
