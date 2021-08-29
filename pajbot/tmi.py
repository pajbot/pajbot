from typing import Any

from enum import Enum


class WhisperOutputMode(Enum):
    DISABLED = 0
    NORMAL = 1
    CHAT = 2

    @staticmethod
    def from_config_value(config_value):
        try:
            return WhisperOutputMode[config_value.upper()]
        except KeyError:
            raise ValueError(
                f'whisper_output_mode config option "{config_value}" was not recognized. Must be `disabled`, `normal` or `chat`'
            )


class TMIRateLimits:
    BASE: Any
    KNOWN: Any
    VERIFIED: Any

    def __init__(self, privmsg_per_30, whispers_per_second, whispers_per_minute):
        self.privmsg_per_30 = privmsg_per_30
        self.whispers_per_second = whispers_per_second
        self.whispers_per_minute = whispers_per_minute


TMIRateLimits.BASE = TMIRateLimits(privmsg_per_30=90, whispers_per_second=2, whispers_per_minute=90)
TMIRateLimits.KNOWN = TMIRateLimits(privmsg_per_30=90, whispers_per_second=2, whispers_per_minute=90)
TMIRateLimits.VERIFIED = TMIRateLimits(privmsg_per_30=90, whispers_per_second=2, whispers_per_minute=90)
