from pajbot.modules.base import BaseModule
from pajbot.modules.base import ModuleSetting
from pajbot.models.command import Command
from pajbot.models.command import CommandExample

class WeatherModule(BaseModule)

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
            key="darksky_location",
            label="Choose the default weather location",
            type="text",
            required=True,
            placeholder="27.4698,153.0251",
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
        location = self.settings["darksky_location"]
        language = self.settings["darksky_language"]
        
        if not self.darksky_key:
            # Notify user of misconfiguration
            return False
            
            query_parameters = {
            "key": self.darksky_key,
            "input": message,
            "output": "json",
            "format": "plaintext",
            "reinterpret": "true",
            "units": "
            }
