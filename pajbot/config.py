from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Tuple, Type, Union

import logging

from pajbot.managers.twitter import GenericTwitterManager, PBTwitterManager, TwitterManager

if TYPE_CHECKING:
    from pajbot.apiwrappers.twitch.helix import TwitchHelixAPI
    from pajbot.models.user import UserBasics

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
        log.warning(
            "DEPRECATED - Specify the streamer's Twitch User ID using streamer_id instead of their login name in streamer"
        )
        return None, config["main"]["streamer"]
    elif "target" in config["main"]:
        log.warning("DEPRECATED - You should specify the streamer using the streamer_id config value")
        return None, config["main"]["target"][1:]

    raise KeyError("Missing streamer_id key from config")


def load_streamer(config: Config, twitch_helix_api: TwitchHelixAPI) -> UserBasics:
    streamer_id, streamer_login = load_streamer_id_or_login(config)
    if streamer_id is not None:
        return twitch_helix_api.require_user_basics_by_id(streamer_id)
    if streamer_login is not None:
        return twitch_helix_api.require_user_basics_by_login(streamer_login)
    raise ValueError("Bad config, missing streamer id or login")


def load_bot_id_or_login(config: Config) -> Union[Tuple[str, None], Tuple[None, str]]:
    """
    Load either the bot Twitch User ID or Twitch User Login from the config
    The Twitch User ID is read from bot_id, and the Twitch User Login us read from nickname

    If neither of the values are present, throw an exception
    """

    if "bot_id" in config["main"]:
        return config["main"]["bot_id"], None
    elif "nickname" in config["main"]:
        log.warning(
            "DEPRECATED - Specify the bot's Twitch User ID using bot_id instead of their login name in nickname"
        )
        return None, config["main"]["nickname"]

    raise KeyError("Missing bot_id key from config")


def load_bot(config: Config, twitch_helix_api: TwitchHelixAPI) -> UserBasics:
    bot_id, bot_login = load_bot_id_or_login(config)
    if bot_id is not None:
        return twitch_helix_api.require_user_basics_by_id(bot_id)
    if bot_login is not None:
        return twitch_helix_api.require_user_basics_by_login(bot_login)
    raise ValueError("Bad config, missing bot id or login")


def load_control_hub_id_or_login(config: Config) -> Union[Tuple[str, None], Tuple[None, str], Tuple[None, None]]:
    """
    Load either the control hub Twitch User ID or Twitch User Login from the config
    The Twitch User ID is read from control_hub_id, and the Twitch User Login us read from control_hub

    If neither of the values are present, throw an exception
    """

    if "control_hub_id" in config["main"]:
        return config["main"]["control_hub_id"], None
    elif "control_hub" in config["main"]:
        log.warning(
            "DEPRECATED - Specify the control hub's Twitch User ID using control_hub_id instead of their login name in control_hub"
        )
        return None, config["main"]["control_hub"]

    return None, None


def load_admin_id_or_login(config: Config) -> Union[Tuple[str, None], Tuple[None, str], Tuple[None, None]]:
    """
    Load either the admin Twitch User ID or Twitch User Login from the config
    The Twitch User ID is read from admin_id, and the Twitch User Login us read from admin

    If neither of the values are present, throw an exception
    """

    if "admin_id" in config["main"]:
        return config["main"]["admin_id"], None
    elif "admin" in config["main"]:
        log.warning(
            "DEPRECATED - Specify the admin's Twitch User ID using admin_id instead of their login name in admin"
        )
        return None, config["main"]["admin"]

    return None, None


def load_twitter_manager(config: Config) -> Type[GenericTwitterManager]:
    if "twitter" in config and config["twitter"].get("streaming_type", "twitter") == "tweet-provider":
        return PBTwitterManager

    return TwitterManager


def get_boolean(o: ConfigSection, key: str, default_value: bool) -> bool:
    v = o.get(key, default_value)

    return v == "1"
