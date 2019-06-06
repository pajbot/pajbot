import json
import logging

import random

from pajbot.managers.redis import RedisManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.emote import Emote, EmoteInstance, EmoteInstanceCount
from pajbot.streamhelper import StreamHelper
from pajbot.utils import iterate_split_with_index

log = logging.getLogger(__name__)


class GenericChannelEmoteManager:
    # to be implemented
    api = None
    redis_name = None
    friendly_name = None

    def __init__(self):
        self._global_emotes = []
        self._channel_emotes = []

        self.global_lookup_table = {}
        self.channel_lookup_table = {}

        self.load_global_emotes()
        self.load_channel_emotes()

    @property
    def channel_emote_redis_key(self):
        streamer = StreamHelper.get_streamer()
        return "{}:emotes:{}_channel_emotes".format(streamer, self.redis_name)

    @property
    def global_emote_redis_key(self):
        return "global:emotes:{}_global_emotes".format(self.redis_name)

    @property
    def global_emotes(self):
        return self._global_emotes

    @global_emotes.setter
    def global_emotes(self, value):
        self._global_emotes = value
        self.global_lookup_table = {emote.code: emote for emote in value} if value is not None else {}

    @property
    def channel_emotes(self):
        return self._channel_emotes

    @channel_emotes.setter
    def channel_emotes(self, value):
        self._channel_emotes = value
        self.channel_lookup_table = {emote.code: emote for emote in value} if value is not None else {}

    @staticmethod
    def load_cached_emotes(redis_key):
        try:
            redis = RedisManager.get()
            redis_result = redis.get(redis_key)
            if redis_result is None:
                return None
            return [Emote(**args) for args in json.loads(redis_result)]
        except:
            log.exception("Failed to get emotes from key {} from redis".format(redis_key))
            return []

    @staticmethod
    def save_cached_emotes(redis_key, emotes):
        try:
            redis = RedisManager.get()
            # emotes expire after 1 hour
            redis.setex(redis_key, 3600, json.dumps(emotes))
        except:
            log.exception("Error saving emotes to redis key {}".format(redis_key))

    def load_global_emotes(self):
        """Load channel emotes from the cache if available, or else, query the API."""
        self.global_emotes = self.load_cached_emotes(self.global_emote_redis_key)

        # no channel emotes in cache? load from API and save to cache.
        if self.global_emotes is None:
            self.update_global_emotes()

    def update_global_emotes(self):
        self.global_emotes = self.api.get_global_emotes()
        self.save_cached_emotes(self.global_emote_redis_key, self.global_emotes)
        log.info("Successfully updated {} global emotes".format(self.friendly_name))

    def load_channel_emotes(self):
        """Load channel emotes from the cache if available, or else, query the API."""
        self.channel_emotes = self.load_cached_emotes(self.channel_emote_redis_key)

        # no channel emotes in cache? load from API and save to cache.
        if self.channel_emotes is None:
            self.update_channel_emotes()

    def update_channel_emotes(self):
        streamer = StreamHelper.get_streamer()
        self.channel_emotes = self.api.get_channel_emotes(streamer)
        self.save_cached_emotes(self.channel_emote_redis_key, self.channel_emotes)
        log.info("Successfully updated {} channel emotes".format(self.friendly_name))

    def update_all(self):
        self.update_global_emotes()
        self.update_channel_emotes()

    def match_channel_emote(self, word):
        """Attempts to find a matching emote equaling the given word from the channel emotes known to this manager.
        Returns None if no emote was matched"""
        return self.channel_lookup_table.get(word, None)

    def match_global_emote(self, word):
        """Attempts to find a matching emote equaling the given word from the global emotes known to this manager.
        Returns None if no emote was matched"""
        return self.global_lookup_table.get(word, None)


class TwitchEmoteManager(GenericChannelEmoteManager):
    redis_name = "twitch"
    friendly_name = "Twitch"

    def __init__(self, client_id):
        from pajbot.apiwrappers import TwitchAPI

        self.api = TwitchAPI(client_id)

        self.tier_one_emotes = []
        self.tier_two_emotes = []
        self.tier_three_emotes = []

        super().__init__()

    @property
    def channel_emotes(self):
        return self.tier_one_emotes

    def update_channel_emotes(self):
        streamer = StreamHelper.get_streamer()
        self.tier_one_emotes, self.tier_two_emotes, self.tier_three_emotes = self.api.get_channel_emotes(streamer)
        self.save_cached_subemotes(
            self.channel_emote_redis_key, self.tier_one_emotes, self.tier_two_emotes, self.tier_three_emotes
        )
        log.info("Successfully updated {} channel emotes".format(self.friendly_name))

    def load_channel_emotes(self):
        """Load channel emotes from the cache if available, or else, query the API."""
        self.tier_one_emotes, self.tier_two_emotes, self.tier_three_emotes = self.load_cached_subemotes(
            self.channel_emote_redis_key
        )

        # no channel emotes in cache? load from API and save to cache.
        if self.tier_one_emotes is None or self.tier_two_emotes is None or self.tier_three_emotes is None:
            self.update_channel_emotes()

    @staticmethod
    def load_cached_subemotes(redis_key):
        try:
            redis = RedisManager.get()
            redis_result = redis.get(redis_key)
            if redis_result is None:
                return None, None, None
            obj = {key: [Emote(**args) for args in value] for key, value in json.loads(redis_result).items()}
            return obj["1"], obj["2"], obj["3"]
        except:
            log.exception("Failed to get subemotes from key {} from redis".format(redis_key))
            return [], [], []

    @staticmethod
    def save_cached_subemotes(redis_key, tier_one, tier_two, tier_three):
        try:
            redis = RedisManager.get()
            # emotes expire after 1 hour
            redis.setex(redis_key, 3600, json.dumps({"1": tier_one, "2": tier_two, "3": tier_three}))
        except:
            log.exception("Error saving subemotes to redis key {}".format(redis_key))


class FFZEmoteManager(GenericChannelEmoteManager):
    redis_name = "ffz"
    friendly_name = "FFZ"

    def __init__(self):
        from pajbot.apiwrappers import FFZApi

        self.api = FFZApi()
        super().__init__()


class BTTVEmoteManager(GenericChannelEmoteManager):
    redis_name = "bttv"
    friendly_name = "BTTV"

    def __init__(self):
        from pajbot.apiwrappers import BTTVApi

        self.api = BTTVApi()
        super().__init__()


class EmoteManager:
    def __init__(self, twitch_client_id):
        self.twitch_emote_manager = TwitchEmoteManager(twitch_client_id)
        self.ffz_emote_manager = FFZEmoteManager()
        self.bttv_emote_manager = BTTVEmoteManager()

        self.epm = {}

        try:
            # every 1 hour
            ScheduleManager.execute_every(60 * 60 * 1, self.bttv_emote_manager.update_all)
            ScheduleManager.execute_every(60 * 60 * 1, self.ffz_emote_manager.update_all)
            ScheduleManager.execute_every(60 * 60 * 1, self.twitch_emote_manager.update_all)
        except:
            log.exception("Something went wrong trying to initialize automatic emote refresh")

    @staticmethod
    def twitch_emote_url(emote_id, size):
        return "https://static-cdn.jtvnw.net/emoticons/v1/{}/{}".format(emote_id, size)

    @staticmethod
    def twitch_emote(emote_id, code):
        return Emote(
            code=code,
            provider="twitch",
            id=emote_id,
            urls={
                "1": EmoteManager.twitch_emote_url(emote_id, "1.0"),
                "2": EmoteManager.twitch_emote_url(emote_id, "2.0"),
                "4": EmoteManager.twitch_emote_url(emote_id, "3.0"),
            },
        )

    @staticmethod
    def twitch_emote_instance(emote_id, code, start, end):
        return EmoteInstance(start=start, end=end, emote=EmoteManager.twitch_emote(emote_id, code))

    @staticmethod
    def parse_twitch_emotes_tag(tag, message):
        if tag is None:
            return []

        emote_instances = []

        for emote_src in tag.split("/"):
            emote_id, emote_instances_src = emote_src.split(":")
            emote_id = int(emote_id)

            for emote_instance_src in emote_instances_src.split(","):
                start_src, end_src = emote_instance_src.split("-")
                start = int(start_src)
                end = int(end_src) + 1
                code = message[start:end]

                emote_instances.append(EmoteManager.twitch_emote_instance(emote_id, code, start, end))

        return emote_instances

    def match_word_to_emote(self, word):
        emote = self.ffz_emote_manager.match_channel_emote(word)
        if emote is not None:
            return emote

        emote = self.bttv_emote_manager.match_channel_emote(word)
        if emote is not None:
            return emote

        emote = self.ffz_emote_manager.match_global_emote(word)
        if emote is not None:
            return emote

        emote = self.bttv_emote_manager.match_global_emote(word)
        if emote is not None:
            return emote

        return None

    def parse_all_emotes(self, message, twitch_emotes_tag):
        # Twitch Emotes
        twitch_emote_instances = self.parse_twitch_emotes_tag(twitch_emotes_tag, message)
        twitch_emote_start_indices = {instance.start for instance in twitch_emote_instances}

        # for the other providers, split the message by spaces
        # and then, if word is not a twitch emote, consider ffz channel -> bttv channel ->
        # ffz global -> bttv global in that order.
        third_party_emote_instances = []

        for current_word_index, word in iterate_split_with_index(message.split(" ")):
            # ignore twitch emotes
            is_twitch_emote = current_word_index in twitch_emote_start_indices
            if is_twitch_emote:
                continue

            emote = self.match_word_to_emote(word)
            if emote is None:
                # this word is not an emote
                continue

            third_party_emote_instances.append(
                EmoteInstance(start=current_word_index, end=current_word_index + len(word), emote=emote)
            )

        all_instances = twitch_emote_instances + third_party_emote_instances
        all_instances.sort(key=lambda instance: instance.start)

        return all_instances, compute_emote_counts(all_instances)

    def random_emote(
        self,
        twitch_global=False,
        twitch_channel_tier1=False,
        twitch_channel_tier2=False,
        twitch_channel_tier3=False,
        ffz_global=False,
        ffz_channel=False,
        bttv_global=False,
        bttv_channel=False,
    ):
        emotes = []
        if twitch_global:
            emotes += self.twitch_emote_manager.global_emotes
        if twitch_channel_tier1:
            emotes += self.twitch_emote_manager.tier_one_emotes
        if twitch_channel_tier2:
            emotes += self.twitch_emote_manager.tier_two_emotes
        if twitch_channel_tier3:
            emotes += self.twitch_emote_manager.tier_three_emotes
        if ffz_global:
            emotes += self.ffz_emote_manager.global_emotes
        if ffz_channel:
            emotes += self.ffz_emote_manager.channel_emotes
        if bttv_global:
            emotes += self.bttv_emote_manager.global_emotes
        if bttv_channel:
            emotes += self.bttv_emote_manager.channel_emotes

        if len(emotes) <= 0:
            return None

        return random.sample(emotes)


def compute_emote_counts(emote_instances):
    """Turns a list of emote instances into a map mapping emote code
    to count and a list of instances."""
    emote_counts = {}
    for emote_instance in emote_instances:
        emote_code = emote_instance.emote.code
        current_value = emote_counts.get(emote_code, None)

        if current_value is None:
            current_value = EmoteInstanceCount(count=1, emote=emote_instance.emote, emote_instances=[emote_instance])
            emote_counts[emote_code] = current_value
        else:
            current_value.count += 1
            current_value.emote_instances.append(emote_instance)

    return emote_counts


class EpmManager:
    def __init__(self):
        self.epm = {}

    def handle_emotes(self, emote_counts):
        # passed dict maps emote code (e.g. "Kappa") to an EmoteInstanceCount instance
        for emote_code, obj in emote_counts.items():
            self.epm_incr(emote_code, obj.count)

    def epm_incr(self, code, count):
        self.epm[code] = self.epm.get(code, 0) + count
        # TODO if we want to add epm records back, do it here
        ScheduleManager.execute_delayed(60, self.epm_decr, args=[code, count])

    def epm_decr(self, code, count):
        self.epm[code] -= count

    def get_emote_epm(self, emote_code):
        """Returns the current "emote per minute" usage of the given emote code,
        or None if the emote is unknown to the bot."""
        return self.epm.get(emote_code, None)


class EcountManager:
    @staticmethod
    def handle_emotes(emote_counts):
        # passed dict maps emote code (e.g. "Kappa") to an EmoteInstanceCount instance
        streamer = StreamHelper.get_streamer()
        redis_key = "{streamer}:emotes:count".format(streamer=streamer)
        with RedisManager.pipeline_context() as redis:
            for emote_code, instance_counts in emote_counts.items():
                redis.zincrby(redis_key, instance_counts.count, emote_code)

    @staticmethod
    def get_emote_count(emote_code):
        redis = RedisManager.get()
        streamer = StreamHelper.get_streamer()
        emote_count = redis.zscore("{streamer}:emotes:count".format(streamer=streamer), emote_code)
        if emote_count is None:
            return None
        return int(emote_count)
