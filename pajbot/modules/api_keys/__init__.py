import logging

from datetime import timedelta

from pajbot.modules import BaseModule, ModuleSetting, ModuleType

log = logging.getLogger(__name__)


class ApiKeyModule(BaseModule):
    ID = "apikeys_group"
    NAME = "API Keys"
    DESCRIPTION = "A place to input your 3rd party API keys."
    CATEGORY = "Feature"
    CONFIGURE_LEVEL = 1500
    ENABLED_DEFAULT = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED
    SETTINGS = [
        ModuleSetting(
            key="safe_browsing_api_key",
            label="Safe Browsing API Key | Used by the LinkChecker Module | Learn more here: https://developers.google.com/safe-browsing/v4",
            type="password",
            required=False,
            placeholder="OWwcxRaHf820gei2PTouLnkUZbEWNo0EXD9cY_0",
            default="",
            constraints={},
        ),
        ModuleSetting(
            key="pnsl_key",
            label="PNSL Key | Required for the PNSL Module | Get your API key here: https://bot.tetyys.com/swagger/index.html",
            type="password",
            required=False,
            placeholder="abcdef",
            default="",
            constraints={},
        ),
        ModuleSetting(
            key="lastfm_key",
            label="LastFM Key | Required for the LastFM Module | Learn more here: https://www.last.fm/api",
            type="password",
            required=False,
            placeholder="abcedfg1235hfhafafajhf",
            default="",
            constraints={},
        ),
        ModuleSetting(
            key="riot_api_key",
            label="Riot Developer API Key | Required for the LeagueRank Module | Learn more here: https://developer.riotgames.com",
            type="password",
            required=False,
            placeholder="1e3415de-1234-5432-f331-67abb0454d12",
            default="",
        ),
        ModuleSetting(
            key="youtube_developer_key",
            label="YouTube Developer Key | Required for the Pleblist Module | Learn more here: https://developers.google.com/youtube/v3/getting-started",
            type="password",
            required=False,
            placeholder="abc",
            default="",
        ),
    ]
