from pajbot.modules.base import BaseModule
from pajbot.modules.base import ModuleSetting
from pajbot.models.command import Command
from pajbot.models.command import CommandExample


class WeatherModule(BaseModule):

    ID =
    NAME = "Weather"
    DESCRIPTION = "Simple module for some weather commands - Powered by Dark Sky: https://darksky.net/poweredby/"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSettings(
            key="temperature_units",
            label="Choose the unit of measurement to use for the temperature - Options can be found here: https://darksky.net/dev/docs",
            type="",
            required=True,
            placeholder="",
            default="auto",
        ),
        ModuleSettings(
            key="darksky_latitude",
            label="Choose the default weather latitude",
            type="text",
            required=True,
            placeholder="-27.46977",
            default="",
        ),
        ModuleSettings(
            key="darksky_longitude",
            label="Choose the default weather longitude",
            type="text",
            required=True,
            placeholder="153.025131",
            default="",
        ),
        ModuleSettings(
            key="darksky_language",
            label="Choose the default language the API should use - Supported list can be found here: https://darksky.net/dev/docs",
            type="text",
            required=True,
            placeholder="",
            default="en",
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)

        if bot:
            self.darksky_key = bot.config["main"].get("darksky", None)

    def query(sec, bot, source, message, event, args):
        latitude = self.settings["darksky_latitude"]
        longitude = self.settings["darksky_longitude"]
        language = self.settings["darksky_language"]
        units = self.settings["temperature_units"]

        if not self.darksky_key:
            # Notify user of misconfiguration
            return False

            query_parameters = {
            "key": self.darksky_key,
            "latitude": self.darksky_latitude,
            "longitude": self.darksky_longitute,
            "lang": self.darksky_language,
            "units": self.temperature_units,
            }

            res = requests.get("https://api.darksky.net/forecast", params=query_parameters)
            answer = res.json()["queryresult"]

            base_reply = f"{source}, "

            is_error = answer["error"]
            is_success = answer["success"]
            log.debug("Result status: error: %s, success: %s", is_error, is_success)

            if is_error:
                reply = base_reply + "your query errored FeelsBadMan"
                bot.send_message_to_user(source, reply, event, method="reply")
                return False

    def load_commands(self, **options)"
        self.commands["weather"] = Command.raw_command(
        self.query,
        delay_all=self.settings["global_cd"],
        delay_user=self.settings["user_cd"],
        level=self.settings["level"],
        description="",
        command="weather",
        examples=[],
    )
    self.commands["temperature"] = self.commands["weather"]
