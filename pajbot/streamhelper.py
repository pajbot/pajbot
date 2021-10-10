from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional, Union

import collections

if TYPE_CHECKING:
    from pajbot.models.stream import StreamManager


class StreamHelper:
    """Staticly available class with a bunch of useful variables.
    streamer: The name of the streamer in full lowercase
    streamer_id: The Twitch user ID of the streamer (a string)
    streamer_display: Display name of streamer
    stream_id: The ID of the current stream. False if the stream is not live
    """

    streamer = "Unknown"
    streamer_id = "Unknown"
    streamer_display = "Unknown"
    stream_manager: Optional[StreamManager] = None
    social_keys_unsorted = {
        "twitter": {"format": "https://twitter.com/{}", "title": "Twitter"},
        "github": {"format": "https://github.com/{}", "title": "Github"},
        "youtube": {"format": "{}", "title": "YouTube"},
        "instagram": {"format": "https://www.instagram.com/{}/", "title": "Instagram"},
        "reddit": {"format": "https://www.reddit.com/r/{}/", "title": "Reddit"},
        "steam": {"format": "{}", "title": "Steam"},
        "facebook": {"format": "{}", "title": "Facebook"},
        "discord": {"format": "https://discord.gg/{}", "title": "Discord"},
        "star": {"format": "{}", "title": "Website"},
        "patreon": {"format": "https://www.patreon.com/{}", "title": "Patreon"},
        "snapchat": {"format": "https://snapchat.com/add/{}", "title": "Snapchat"},
    }
    social_keys = collections.OrderedDict(sorted(social_keys_unsorted.items(), key=lambda t: t[0]))
    valid_social_keys = set(social_keys.keys())

    @staticmethod
    def init_stream_manager(stream_manager: StreamManager) -> None:
        StreamHelper.stream_manager = stream_manager

    @staticmethod
    def init_streamer(streamer: str, streamer_id: str, streamer_display: str) -> None:
        StreamHelper.streamer = streamer
        StreamHelper.streamer_id = streamer_id
        StreamHelper.streamer_display = streamer_display

    @staticmethod
    def get_streamer() -> str:
        return StreamHelper.streamer

    @staticmethod
    def get_streamer_id() -> str:
        return StreamHelper.streamer_id

    @staticmethod
    def get_streamer_display() -> str:
        return StreamHelper.streamer_display

    @staticmethod
    def get_current_stream_id() -> Union[None, Literal[False], int]:
        """Gets the stream ID of the current stream.
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
    def get_last_stream_id() -> Union[None, Literal[False], int]:
        """Gets the stream ID of the last stream.
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
    def get_viewers() -> int:
        """Returns how many viewers are currently watching the stream.
        Returns 0 if something fails
        """

        if StreamHelper.stream_manager is None:
            # Stream manager not initialized, web interface?
            return 0

        if StreamHelper.stream_manager.current_stream is None:
            # Stream is offline
            return 0

        return StreamHelper.stream_manager.num_viewers
