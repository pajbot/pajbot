from pajbot.modules.base import BaseModule
from pajbot.modules.base import ModuleSetting

class WeatherModule(BaseModule)

    ID = 
    NAME = "Weather"
    DESCRIPTION = "Simple module for some weather commands"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSettings(
            key="temperature_unit",
            label="Choose the unit of measurement to use for the temperature",
            type="",
            required="true",
            placeholder="",
            default="Celsius",
        ),
    ]
