from enum import Enum


class Whispers(Enum):
    DISABLED = 0
    NORMAL = 1
    CHAT = 2

    @staticmethod
    def from_config_value(config_value):
        return {"disabled": Whispers.DISABLED, "normal": Whispers.NORMAL, "chat": Whispers.CHAT}.get(
            config_value.lower(), Whispers.NORMAL
        )


class TMI:
    message_limit = 90
    whispers = Whispers.NORMAL
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

    @staticmethod
    def change_whispers(setting):
        TMI.whispers = setting
