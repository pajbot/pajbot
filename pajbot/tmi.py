class TMI:
    message_limit = 90
    whispers_message_limit_second = 2
    whispers_message_limit_minute = 90

    @staticmethod
    def promote_to_verified():
        TMI.message_limit = 7000
        TMI.whispers_message_limit_second = 15
        TMI.whispers_message_limit_minute = 1150
