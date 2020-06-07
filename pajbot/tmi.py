from enum import Enum


class WhisperOutputMode(Enum):
    DISABLED = 0
    NORMAL = 1
    CHAT = 2

    CONFIG_OPTIONS = {
        "disabled": WhisperOutputMode.DISABLED,
        "normal": WhisperOutputMode.NORMAL,
        "chat": WhisperOutputMode.CHAT,
    }

    @staticmethod
    def from_config_value(config_value):
        if config_value.lower() in CONFIG_OPTIONS:
            return CONFIG_OPTIONS[config_value.lower()]
        else:
            raise ValueError(f"whisper_output_mode config option \"{config_value}\" was not recognized. Must be `disabled`, `normal` or `chat`")


class TMI:
    message_limit = 90
    whisper_output_mode = WhisperOutputMode.NORMAL
    whispers_message_limit_second = 2
    whispers_message_limit_minute = 90

    @staticmethod
    def promote_to_verified():
        TMI.message_limit = 7000
        TMI.whispers_message_limit_second = 15
        TMI.whispers_message_limit_minute = 1150

    @staticmethod
    def promote_to_known():
        TMI.whispers_message_limit_second = 8
        TMI.whispers_message_limit_minute = 180
