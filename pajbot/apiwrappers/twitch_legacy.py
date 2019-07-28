import logging

from requests import HTTPError

from pajbot.apiwrappers.twitch_common import BaseTwitchApi

log = logging.getLogger(__name__)


class LegacyTwitchApi(BaseTwitchApi):
    authorization_header_prefix = "OAuth "

    def __init__(self, client_id=None, oauth=None):
        super().__init__("https://api.twitch.tv/api/", client_id, oauth)

    def get_channel_emotes(self, channel):
        """Returns a tuple of three lists of emotes, each one corresponding to tier 1, tier 2 and tier 3 respectively.
        Tier 2 and Tier 3 ONLY contain the respective extra emotes added to that tier, typically tier 2 and tier 3
        will contain exactly one or zero emotes."""
        # circular import prevention
        from pajbot.managers.emote import EmoteManager

        try:
            resp = self.get("/channels/{}/product".format(self.quote_path_param(channel)))
            plans = resp["plans"]
            if len(plans) <= 0:
                log.warning("No subscription plans found for channel {}".format(channel))
                return [], [], []

            # plans[0] is tier 1
            ret_data = []
            already_visited_plans = set()
            for plan in plans:
                emotes = [
                    EmoteManager.twitch_emote(data["id"], data["regex"])
                    for data in plan["emoticons"]
                    if data["emoticon_set"] not in already_visited_plans
                ]
                ret_data.append(emotes)
                already_visited_plans.update(plan["emoticon_set_ids"])

            # fill up to form at least three lists of emotes
            for i in range(len(ret_data), 3):
                ret_data[i] = []

            return tuple(ret_data)

        except HTTPError as e:
            if e.response.status_code == 404:
                log.warning("No sub emotes found for channel {}".format(channel))
                return [], [], []
            else:
                raise e
