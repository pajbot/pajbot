import logging

from requests import HTTPError

from pajbot.apiwrappers.response_cache import TwitchChannelEmotesSerializer
from pajbot.apiwrappers.base import BaseAPI

log = logging.getLogger(__name__)


class TwitchEmotesAPI(BaseAPI):
    def __init__(self, redis):
        super().__init__(base_url="https://api.twitchemotes.com/api/v4/", redis=redis)

    def fetch_channel_emotes(self, channel_id, channel_name):
        """Returns a tuple of three lists of emotes, each one corresponding to tier 1, tier 2 and tier 3 respectively.
        Tier 2 and Tier 3 ONLY contain the respective extra emotes added to that tier, typically tier 2 and tier 3
        will contain exactly one or zero emotes."""
        # circular import prevention
        from pajbot.managers.emote import EmoteManager

        try:
            resp = self.get(["channels", channel_id])
            plans = resp["plans"]
            if len(plans) <= 0:
                log.warning(f"No subscription plans found for channel {channel_name}")
                return [], [], []

            # plans["$4.99"] is tier 1
            # plans["$9.99"] is tier 2
            # plans["$24.99"] is tier 1
            ret_data = ([], [], [])
            for emote in resp["emotes"]:
                tier = 0
                if str(emote["emoticon_set"]) == str(plans["$4.99"]):  # tier 1 emotes
                    tier = 1
                elif str(emote["emoticon_set"]) == str(plans["$9.99"]):
                    tier = 2
                else:
                    tier = 3
                ret_data[tier - 1].append(EmoteManager.twitch_emote(emote["id"], emote["code"]))
            return ret_data

        except HTTPError as e:
            if e.response.status_code == 404:
                log.warning(f"No sub emotes found for channel {channel_name}")
                return [], [], []
            else:
                raise e

    def get_channel_emotes(self, channel_id, channel_name, force_fetch=False):
        return self.cache.cache_fetch_fn(
            redis_key=f"api:twitch_emotes:channel-emotes:{channel_name}",
            fetch_fn=lambda: self.fetch_channel_emotes(channel_id, channel_name),
            serializer=TwitchChannelEmotesSerializer(),
            expiry=60 * 60,
            force_fetch=force_fetch,
        )
