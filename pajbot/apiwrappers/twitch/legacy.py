import logging

from requests import HTTPError

from pajbot.apiwrappers.response_cache import TwitchChannelEmotesSerializer
from pajbot.apiwrappers.twitch.base import BaseTwitchAPI

log = logging.getLogger(__name__)


class TwitchLegacyAPI(BaseTwitchAPI):
    authorization_header_prefix = "OAuth"

    def __init__(self, client_credentials, redis):
        super().__init__(base_url="https://api.twitch.tv/api/", redis=redis)
        self.client_credentials = client_credentials

    @property
    def default_authorization(self):
        return self.client_credentials

    def fetch_channel_emotes(self, channel_name):
        """Returns a tuple of three lists of emotes, each one corresponding to tier 1, tier 2 and tier 3 respectively.
        Tier 2 and Tier 3 ONLY contain the respective extra emotes added to that tier, typically tier 2 and tier 3
        will contain exactly one or zero emotes."""
        # circular import prevention
        from pajbot.managers.emote import EmoteManager

        try:
            resp = self.get(["channels", channel_name, "product"])
            plans = resp["plans"]
            if len(plans) <= 0:
                log.warning("No subscription plans found for channel {}".format(channel_name))
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
                log.warning("No sub emotes found for channel {}".format(channel_name))
                return [], [], []
            else:
                raise e

    def get_channel_emotes(self, channel_name, force_fetch=False):
        return self.cache.cache_fetch_fn(
            redis_key="api:twitch:legacy:channel-emotes:{}".format(channel_name),
            fetch_fn=lambda: self.fetch_channel_emotes(channel_name),
            serializer=TwitchChannelEmotesSerializer(),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )
