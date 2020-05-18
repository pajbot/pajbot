class TMI:
    message_limit = 90
    whisper_output = 1
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
    def change_whisper_output(whisper_output):
        TMI.disable_whisper = whisper_output
