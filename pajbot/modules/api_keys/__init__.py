import logging

from datetime import timedelta

from pajbot.managers.handler import HandlerManager
from pajbot.modules.base import BaseModule
from pajbot.modules.base import ModuleSetting
from pajbot.modules.base import ModuleType

log = logging.getLogger(__name__)


class ApiKeyModule(BaseModule):

    ID = "apikeys-group"
    NAME = "API Keys"
    DESCRIPTION = "A place to input your 3rd party API keys."
    CATEGORY = "Feature"
    CONFIGURE_LEVEL = 1500
    ENABLED_DEFAULT = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED
    SETTINGS = [
        ModuleSetting(
            key="safe_browsing_api_key",
            label="Safe Browsing API Key | Used by the LinkChecker Module | Get your API key here: https://developers.google.com/safe-browsing/v4",
            type="text",
            required=False,
            placeholder="OWwcxRaHf820gei2PTouLnkUZbEWNo0EXD9cY_0",
            default="",
            constraints={},
        ),
        ModuleSetting(
            key="pnsl_key",
            label="PNSL Key | Required for the PNSL Module | Get your API key here: https://bot.tetyys.com/swagger/index.html",
            type="text",
            required=False,
            placeholder="abcdef",
            default="",
            constraints={},
        ),
        ModuleSetting(
            key="lastfm_key",
            label="LastFM Key | Required for the LastFM Module | Get your API key here: https://www.last.fm/api/account/create",
            type="text",
            required=False,
	    placeholder="abcedfg1235hfhafafajhf",
            default="",
            constraints={},
       ),
       ModuleSetting(
	    key="riot_api_key",
	    label="Riot Developer API Key | Required for the LeagueRank Module",
	    type="text",
	    required=False,
	    placeholder="1e3415de-1234-5432-f331-67abb0454d12",
	    default="",
       ),
       ModuleSetting(
	    key="youtube_developer_key",
	    label="YouTube Developer Key | Required for the Pleblist Module",
	    type="text",
	    required=False,
	    placeholder="abc",
	    default="",
       ),
    ]
