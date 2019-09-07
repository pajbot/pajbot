import logging

from pajbot.apiwrappers.twitch.base import BaseTwitchAPI

log = logging.getLogger(__name__)


class TwitchTMIAPI(BaseTwitchAPI):
    authorization_header_prefix = "OAuth"

    def __init__(self, client_credentials, redis):
        super().__init__(base_url="https://tmi.twitch.tv/", redis=redis)
        self.session.headers["Accept"] = "application/vnd.twitchtv.v5+json"
        self.client_credentials = client_credentials

    @property
    def default_authorization(self):
        return self.client_credentials

    def get_chatters(self, streamer):
        response = self.get(["group", "user", streamer, "chatters"])
        ch = response["chatters"]

        log.debug(ch)

        chatters = ch["vips"] + ch["moderators"] + ch["staff"] + ch["admins"] + ch["global_mods"] + ch["viewers"]

        return chatters
