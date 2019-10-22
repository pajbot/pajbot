import collections


class StreamHelper:
    """ Staticly available class with a bunch of useful variables.
    streamer: The name of the streamer in full lowercase
    streamer_id: The Twitch user ID of the streamer (a string)
    stream_id: The ID of the current stream. False if the stream is not live
    """

    streamer = "Unknown"
    streamer_id = "Unknown"
    stream_manager = None
    social_keys_unsorted = {
        "twitter": {"format": "https://twitter.com/{}", "title": "Twitter"},
        "github": {"format": "https://github.com/{}", "title": "Github"},
        "youtube": {"format": "{}", "title": "YouTube"},
        "instagram": {"format": "https://www.instagram.com/{}/", "title": "Instagram"},
        "reddit": {"format": "https://www.reddit.com/r/{}/", "title": "Reddit"},
        "steam": {"format": "{}", "title": "Steam"},
        "facebook": {"format": "{}", "title": "Facebook"},
        "star": {"format": "{}", "title": "Website"},
    }
    social_keys = collections.OrderedDict(sorted(social_keys_unsorted.items(), key=lambda t: t[0]))
    valid_social_keys = set(social_keys.keys())

    @staticmethod
    def init_stream_manager(stream_manager):
        StreamHelper.stream_manager = stream_manager

    @staticmethod
    def init_streamer(streamer, streamer_id):
        StreamHelper.streamer = streamer
        StreamHelper.streamer_id = streamer_id

    @staticmethod
    def get_streamer():
        return StreamHelper.streamer

    @staticmethod
    def get_streamer_id():
        return StreamHelper.streamer_id

    @staticmethod
    def get_current_stream_id():
        """ Gets the stream ID of the current stream.
        Returns None if the stream manager has not been initialized.
        Returns False if there is no stream online.
        Returns the current streams ID (integer) otherwise.
        """

        if StreamHelper.stream_manager is None:
            # Stream manager not initialized, web interface?
            return None

        if StreamHelper.stream_manager.current_stream is None:
            # Stream is offline
            return False

        return StreamHelper.stream_manager.current_stream.id

    @staticmethod
    def get_last_stream_id():
        """ Gets the stream ID of the last stream.
        Returns None if the stream manager has not been initialized.
        Returns False if there is no stream online.
        Returns the current streams ID (integer) otherwise.
        """

        if StreamHelper.stream_manager is None:
            # Stream manager not initialized, web interface?
            return None

        if StreamHelper.stream_manager.last_stream is None:
            # Stream is offline
            return False

        return StreamHelper.stream_manager.last_stream.id

    @staticmethod
    def get_viewers():
        """ Returns how many viewers are currently watching the stream.
        Returns 0 if something fails
        """

        if StreamHelper.stream_manager is None:
            # Stream manager not initialized, web interface?
            return 0

        if StreamHelper.stream_manager.current_stream is None:
            # Stream is offline
            return 0

        return StreamHelper.stream_manager.num_viewers
