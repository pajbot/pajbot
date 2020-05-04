import logging

from datetime import timedelta

from pajbot.managers.handler import HandlerManager
from pajbot.modules.base import BaseModule
from pajbot.modules.base import ModuleSetting
from pajbot.modules.base import ModuleType
from pajbot.modules.api_keys import ApiKeyModule

log = logging.getLogger(__name__)


class WolframKeysModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Wolfram Alpha Keys"
    DESCRIPTION = "A place to input your Wolfram Alpha Key | Get your API key here: http://developer.wolframalpha.com/portal/myapps"
    CATEGORY = "Feature"
    CONFIGURE_LEVEL = 1500
    ENABLED_DEFAULT = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED
    PARENT_MODULE = ApiKeyModule
    SETTINGS = [
       ModuleSetting(
           key="wolfram_key",
           label="Wolfram Alpha Key | Get your API key here: http://developer.wolframalpha.com/portal/myapps",
           type="text",
           required=False,
           placeholder="ABCDEF-GHIJKLMNOP",
           default="",
           constraints={},
       ),
       ModuleSetting(
           key="wolfram_ip",
           label="Wolfram Alpha IP | This IP is used to localize the queries to a default location",
           type="text",
           required=False,
           placeholder="62.41.0.123",
           default="",
           constraints={},
       ),
       ModuleSetting(
           key="wolfram_location",
           label="Wolfram Alpha Location | This location it used to localize the queries to a default location. If you specify both IP & Location, the location will be ignored.",
           type="text",
           required=False,
           placeholder="Amsterdam",
           default="",
           constraints={},
       ),
     ]
