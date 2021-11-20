from typing import Dict, Tuple, Type, Union

import logging

from pajbot.managers.twitter import GenericTwitterManager, PBTwitterManager, TwitterManager

ConfigSection = Dict[str, str]
Config = Dict[str, ConfigSection]

log = logging.getLogger(__name__)


def load_streamer_id_or_login(config: Config) -> Union[Tuple[str, None], Tuple[None, str]]:
    """
    Load either the streamer Twitch User ID or Twitch User Login from the config
    The Twitch User ID is read from streamer_id, and the Twitch User Login us read from streamer
    To support old configs, we can also parse the Twitch User Login from target, but this should not be used in new configs.

    If none of the values are present, throw an exception
    """

    if "streamer_id" in config["main"]:
        return config["main"]["streamer_id"], None
    elif "streamer" in config["main"]:
        return None, config["main"]["streamer"]
    elif "target" in config["main"]:
        log.warning("DEPRECATED - You should specify the streamer using the streamer_id config value")
        return None, config["main"]["target"][1:]

    raise KeyError("Missing streamer_id key from config")


def load_bot_id_or_login(config: Config) -> Union[Tuple[str, None], Tuple[None, str]]:
    """
    Load either the bot Twitch User ID or Twitch User Login from the config
    The Twitch User ID is read from bot_id, and the Twitch User Login us read from nickname

    If neither of the values are present, throw an exception
    """

    if "bot_id" in config["main"]:
        return config["main"]["bot_id"], None
    elif "nickname" in config["main"]:
        return None, config["main"]["bot"]

    raise KeyError("Missing bot_id key from config")


def load_control_hub_id_or_login(config: Config) -> Union[Tuple[str, None], Tuple[None, str]]:
    """
    Load either the control hub Twitch User ID or Twitch User Login from the config
    The Twitch User ID is read from control_hub_id, and the Twitch User Login us read from control_hub

    If neither of the values are present, throw an exception
    """

    if "control_hub_id" in config["main"]:
        return config["main"]["control_hub_id"], None
    elif "nickname" in config["main"]:
        return None, config["main"]["control_hub"]

    raise KeyError("Missing control_hub_id key from config")


def load_twitter_manager(config: Config) -> Type[GenericTwitterManager]:
    if "twitter" in config and config["twitter"].get("streaming_type", "twitter") == "tweet-provider":
        return PBTwitterManager

    return TwitterManager


def get_boolean(o: ConfigSection, key: str, default_value: bool) -> bool:
    v = o.get(key, default_value)

    return v == "1"
