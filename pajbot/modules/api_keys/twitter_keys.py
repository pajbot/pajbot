import logging

from datetime import timedelta

from pajbot.managers.handler import HandlerManager
from pajbot.modules.base import BaseModule
from pajbot.modules.base import ModuleSetting
from pajbot.modules.base import ModuleType
from pajbot.modules.api_keys import ApiKeyModule

log = logging.getLogger(__name__)


class TwitterKeyModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Twitter Keys"
    DESCRIPTION = (
        "A place to input your Twitter API keys | Get your API keys here: https://developer.twitter.com/en/apps"
    )
    CATEGORY = "Feature"
    CONFIGURE_LEVEL = 1500
    ENABLED_DEFAULT = True
    MODULE_TYPE = ModuleType.TYPE_ALWAYS_ENABLED
    PARENT_MODULE = ApiKeyModule
    SETTINGS = [
        ModuleSetting(
            key="twitter_consumer_key",
            label="Consumer API Key",
            type="text",
            required=False,
            placeholder="abc",
            default="",
            constraints={},
        ),
        ModuleSetting(
            key="twitter_consumer_secret",
            label="Consumer API Secret Key",
            type="text",
            required=False,
            placeholder="abc",
            default="",
            constraints={},
        ),
        ModuleSetting(
            key="twitter_access_token",
            label="Access Token",
            type="text",
            required=False,
            placeholder="123-abc",
            default="",
            constraints={},
        ),
        ModuleSetting(
            key="twitter_access_token_secret",
            label="Access Token Secret",
            type="text",
            required=False,
            placeholder="abc",
            default="",
            constraints={},
        ),
        ModuleSetting(
            key="twitter_streaming",
            label="Twitter Streaming",
            type="number",
            required=True,
            placeholder="",
            default=1,
            constraints={"min_value": 0, "max_value": 1},
        ),
        ModuleSetting(
            key="twitter_streaming_type",
            label="Twitter Streaming Type",
            type="options",
            required=True,
            default="twitter",
            options=["twitter", "tweet-provider"],
        ),
        ModuleSetting(
            key="tweet_provider_host",
            label="Tweet-Provider Host",
            type="text",
            required=False,
            placeholder="127.0.0.1",
            default="",
            constraints={},
        ),
        ModuleSetting(
            key="tweet_provider_port",
            label="Tweet-Provider Port",
            type="number",
            required=False,
            placeholder="2356",
            default="",
            constraints={},
        ),
        ModuleSetting(
            key="tweet_provider_protocol",
            label="Tweet-Provider Protocol | Note: wss is untested",
            type="options",
            required=False,
            default="ws",
            options=["ws", "wss"],
        ),
    ]
