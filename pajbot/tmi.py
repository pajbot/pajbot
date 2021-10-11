from __future__ import annotations

from enum import Enum


class WhisperOutputMode(Enum):
    DISABLED = 0
    NORMAL = 1
    CHAT = 2
    CONTROL_HUB = 3

    @staticmethod
    def from_config_value(config_value: str) -> WhisperOutputMode:
        try:
            return WhisperOutputMode[config_value.upper()]
        except KeyError:
            raise ValueError(
                f'whisper_output_mode config option "{config_value}" was not recognized. Must be `disabled`, `normal`, `chat` or `control_hub`'
            )


class TMIRateLimits:
    BASE: TMIRateLimits
    KNOWN: TMIRateLimits
    VERIFIED: TMIRateLimits

    def __init__(self, privmsg_per_30: int, whispers_per_second: int, whispers_per_minute: int) -> None:
        self.privmsg_per_30 = privmsg_per_30
        self.whispers_per_second = whispers_per_second
        self.whispers_per_minute = whispers_per_minute


TMIRateLimits.BASE = TMIRateLimits(privmsg_per_30=90, whispers_per_second=2, whispers_per_minute=90)
TMIRateLimits.KNOWN = TMIRateLimits(privmsg_per_30=90, whispers_per_second=2, whispers_per_minute=90)
TMIRateLimits.VERIFIED = TMIRateLimits(privmsg_per_30=90, whispers_per_second=2, whispers_per_minute=90)

CHARACTER_LIMIT = 500
