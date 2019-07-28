from pajbot.apiwrappers.apiwrappers import BaseApi, fill_in_url_scheme
from pajbot.models.emote import Emote


class FFZApi(BaseApi):
    def __init__(self):
        super().__init__(base_url="https://api.frankerfacez.com/v1/")

    @staticmethod
    def parse_sets(emote_sets):
        emotes = []
        for emote_set in emote_sets.values():
            for emote in emote_set["emoticons"]:
                # FFZ returns relative URLs (e.g. //cdn.frankerfacez.com/...)
                # so we fill in the scheme if it's missing :)
                urls = {size: fill_in_url_scheme(url) for size, url in emote["urls"].items()}
                emotes.append(Emote(code=emote["name"], provider="ffz", id=emote["id"], urls=urls))

        return emotes

    def get_global_emotes(self):
        """Returns a list of global FFZ emotes in the standard Emote format."""

        data = self.get("/set/global")

        # FFZ returns a number of global sets but only a subset of them should be available
        # in all channels, those are available under "default_sets", e.g. a list of set IDs like this:
        # [ 3, 6, 7, 14342 ]
        global_set_ids = data["default_sets"]
        global_sets = {str(set_id): data["sets"][str(set_id)] for set_id in global_set_ids}

        return self.parse_sets(global_sets)

    def get_channel_emotes(self, channel_name):
        """Returns a list of channel-specific FFZ emotes in the standard Emote format."""
        data = self.get("/room/{}".format(self.quote_path_param(channel_name)))
        return self.parse_sets(data["sets"])
