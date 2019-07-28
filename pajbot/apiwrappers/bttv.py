from pajbot.apiwrappers.apiwrappers import BaseApi, fill_in_url_scheme
from pajbot.models.emote import Emote


class BTTVApi(BaseApi):
    def __init__(self):
        super().__init__(base_url="https://api.betterttv.net/2/")

    @staticmethod
    def parse_emotes(api_response_data):
        # get with default fallback
        url_template = api_response_data.get("urlTemplate", "//cdn.betterttv.net/emote/{{id}}/{{image}}")
        url_template = fill_in_url_scheme(url_template)

        def get_url(emote_hash, size):
            return url_template.replace("{{id}}", emote_hash).replace("{{image}}", size + "x")

        emotes = []
        for emote in api_response_data["emotes"]:
            emote_hash = emote["id"]
            emotes.append(
                Emote(
                    code=emote["code"],
                    provider="bttv",
                    id=emote_hash,
                    urls={"1": get_url(emote_hash, "1"), "2": get_url(emote_hash, "2"), "4": get_url(emote_hash, "3")},
                )
            )
        return emotes

    def get_global_emotes(self):
        """Returns a list of global BTTV emotes in the standard Emote format."""
        return self.parse_emotes(self.get("/emotes"))

    def get_channel_emotes(self, channel_name):
        """Returns a list of channel-specific BTTV emotes in the standard Emote format."""
        return self.parse_emotes(self.get("/channels/{}".format(self.quote_path_param(channel_name))))
