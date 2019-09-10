import logging

from pajbot.apiwrappers.twitch.base import BaseTwitchAPI

log = logging.getLogger(__name__)


class TwitchTMIAPI(BaseTwitchAPI):
    def __init__(self):
        super().__init__(base_url="https://tmi.twitch.tv/")
        self.session.headers["Accept"] = "application/vnd.twitchtv.v5+json"

    def fetch_chatters(self, streamer):
        response = self.get(["group", "user", streamer, "chatters"])
        ch = response["chatters"]
        chatters = []

        for chatter_category in chatters:
            chatters.extend(chatter_category)

        return chatters
