from enum import Enum


class WhisperOutputMode(Enum):
    DISABLED = 0
    NORMAL = 1
    CHAT = 2

    @staticmethod
    def from_config_value(config_value):
        return {
            "disabled": WhisperOutputMode.DISABLED,
            "normal": WhisperOutputMode.NORMAL,
            "chat": WhisperOutputMode.CHAT,
        }.get(config_value.lower(), WhisperOutputMode.NORMAL)


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
