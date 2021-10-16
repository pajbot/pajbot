from typing import Dict, Tuple, Type

from pajbot.managers.twitter import GenericTwitterManager, PBTwitterManager, TwitterManager

ConfigSection = Dict[str, str]
Config = Dict[str, ConfigSection]


def load_streamer_and_channel(config: Config) -> Tuple[str, str]:
    if "streamer" in config["main"]:
        streamer = config["main"]["streamer"]
        return streamer, f"#{streamer}"
    elif "target" in config["main"]:
        channel = config["main"]["target"]
        return f"{channel[1:]}", channel

    raise KeyError("Missing streamer key from config")


def load_twitter_manager(config: Config) -> Type[GenericTwitterManager]:
    if "twitter" in config and config["twitter"].get("streaming_type", "twitter") == "tweet-provider":
        return PBTwitterManager

    return TwitterManager


def get_boolean(o: ConfigSection, key: str, default_value: bool) -> bool:
    v = o.get(key, default_value)

    return v == "1"
