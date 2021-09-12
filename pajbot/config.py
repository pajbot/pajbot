from typing import Any, Dict, Tuple, Type

from pajbot.managers.twitter import GenericTwitterManager, PBTwitterManager, TwitterManager

Config = Dict[str, Dict[str, Any]]


def load_streamer_and_channel(config) -> Tuple[str, str]:
    if "streamer" in config["main"]:
        streamer = config["main"]["streamer"]
        return streamer, f"#{streamer}"
    elif "target" in config["main"]:
        channel = config["main"]["target"]
        return f"{channel[1:]}", channel

    raise KeyError("Missing streamer key from config")


def load_twitter_manager(config) -> Type[GenericTwitterManager]:
    if "twitter" in config and config["twitter"].get("streaming_type", "twitter") == "tweet-provider":
        return PBTwitterManager

    return TwitterManager
