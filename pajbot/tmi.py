class TMI:
    message_limit = 90
    whispers_message_limit = 20
    whispers_limit_interval = 5  # in seconds

    @staticmethod
    def promote_to_verified():
        TMI.message_limit = 7000
