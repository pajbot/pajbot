from typing import Dict, List, Optional, Protocol, Tuple

import logging
import random

from pajbot.managers.redis import RedisManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.emote import Emote, EmoteInstance, EmoteInstanceCount
from pajbot.streamhelper import StreamHelper
from pajbot.utils import iterate_split_with_index

EmoteInstanceCountMap = Dict[str, EmoteInstanceCount]

log = logging.getLogger(__name__)


class EmoteAPI(Protocol):
    def get_global_emotes(self, force_fetch: bool = ...) -> List[Emote]:
        ...

    def get_channel_emotes(self, streamer_name: str, force_fetch: bool = ...) -> List[Emote]:
        ...


class GenericChannelEmoteManager:
    friendly_name: str

    # to be implemented
    def __init__(self, api: Optional[EmoteAPI]) -> None:
        self._global_emotes: List[Emote] = []
        self._channel_emotes: List[Emote] = []
        self.streamer = StreamHelper.get_streamer()
        self.streamer_id = StreamHelper.get_streamer_id()
        self.global_lookup_table: Dict[str, Emote] = {}
        self.channel_lookup_table: Dict[str, Emote] = {}

        self.api = api

    @property
    def global_emotes(self) -> List[Emote]:
        return self._global_emotes

    @global_emotes.setter
    def global_emotes(self, value: List[Emote]) -> None:
        self._global_emotes = value
        self.global_lookup_table = {emote.code: emote for emote in value} if value is not None else {}

    @property
    def channel_emotes(self) -> List[Emote]:
        return self._channel_emotes

    @channel_emotes.setter
    def channel_emotes(self, value: List[Emote]) -> None:
        self._channel_emotes = value
        self.channel_lookup_table = {emote.code: emote for emote in value} if value is not None else {}

    def load_global_emotes(self) -> None:
        """Load channel emotes from the cache if available, or else, query the API."""
        if self.api is None:
            raise ValueError("API not initialized in Emote Manager")

        self.global_emotes = self.api.get_global_emotes()

    def update_global_emotes(self) -> None:
        if self.api is None:
            raise ValueError("API not initialized in Emote Manager")

        self.global_emotes = self.api.get_global_emotes(force_fetch=True)

    def load_channel_emotes(self) -> None:
        """Load channel emotes from the cache if available, or else, query the API."""
        if self.api is None:
            raise ValueError("API not initialized in Emote Manager")

        self.channel_emotes = self.api.get_channel_emotes(self.streamer)

    def update_channel_emotes(self) -> None:
        if self.api is None:
            raise ValueError("API not initialized in Emote Manager")

        self.channel_emotes = self.api.get_channel_emotes(self.streamer, force_fetch=True)

    def update_all(self) -> None:
        self.update_global_emotes()
        self.update_channel_emotes()

    def load_all(self) -> None:
        self.load_global_emotes()
        self.load_channel_emotes()

    def match_channel_emote(self, word: str) -> Optional[Emote]:
        """Attempts to find a matching emote equaling the given word from the channel emotes known to this manager.
        Returns None if no emote was matched"""
        return self.channel_lookup_table.get(word, None)

    def match_global_emote(self, word: str) -> Optional[Emote]:
        """Attempts to find a matching emote equaling the given word from the global emotes known to this manager.
        Returns None if no emote was matched"""
        return self.global_lookup_table.get(word, None)


class TwitchEmoteManager(GenericChannelEmoteManager):
    friendly_name = "Twitch"

    def __init__(self, twitch_helix_api) -> None:
        self.twitch_helix_api = twitch_helix_api
        self.streamer = StreamHelper.get_streamer()
        self.streamer_id = StreamHelper.get_streamer_id()
        self.tier_one_emotes: List[Emote] = []
        self.tier_two_emotes: List[Emote] = []
        self.tier_three_emotes: List[Emote] = []

        super().__init__(None)

    @property  # type: ignore
    def channel_emotes(self) -> List[Emote]:
        return self.tier_one_emotes

    def load_global_emotes(self) -> None:
        self.global_emotes = self.twitch_helix_api.get_global_emotes()

    def update_global_emotes(self) -> None:
        self.global_emotes = self.twitch_helix_api.get_global_emotes(force_fetch=True)

    def load_channel_emotes(self) -> None:
        self.tier_one_emotes, self.tier_two_emotes, self.tier_three_emotes = self.twitch_helix_api.get_channel_emotes(
            self.streamer_id, self.streamer
        )

    def update_channel_emotes(self) -> None:
        self.tier_one_emotes, self.tier_two_emotes, self.tier_three_emotes = self.twitch_helix_api.get_channel_emotes(
            self.streamer_id, self.streamer, force_fetch=True
        )


class FFZEmoteManager(GenericChannelEmoteManager):
    friendly_name = "FFZ"

    def __init__(self) -> None:
        from pajbot.apiwrappers.ffz import FFZAPI

        super().__init__(FFZAPI(RedisManager.get()))


class BTTVEmoteManager(GenericChannelEmoteManager):
    friendly_name = "BTTV"

    def __init__(self) -> None:
        from pajbot.apiwrappers.bttv import BTTVAPI

        self.streamer = StreamHelper.get_streamer()
        self.streamer_id = StreamHelper.get_streamer_id()

        self.bttv_api = BTTVAPI(RedisManager.get())

        super().__init__(self.bttv_api)

    def load_channel_emotes(self) -> None:
        """Load channel emotes from the cache if available, or else, query the API."""
        self.channel_emotes = self.bttv_api.get_channel_emotes(self.streamer_id)

    def update_channel_emotes(self) -> None:
        self.channel_emotes = self.bttv_api.get_channel_emotes(self.streamer_id, force_fetch=True)


class SevenTVEmoteManager(GenericChannelEmoteManager):
    friendly_name = "7TV"

    def __init__(self) -> None:
        from pajbot.apiwrappers.seventv import SevenTVAPI

        super().__init__(SevenTVAPI(RedisManager.get()))


class EmoteManager:
    def __init__(self, twitch_helix_api, action_queue) -> None:
        self.action_queue = action_queue
        self.streamer = StreamHelper.get_streamer()
        self.streamer_id = StreamHelper.get_streamer_id()
        self.twitch_emote_manager = TwitchEmoteManager(twitch_helix_api)
        self.ffz_emote_manager = FFZEmoteManager()
        self.bttv_emote_manager = BTTVEmoteManager()
        self.seventv_emote_manager = SevenTVEmoteManager()

        # every 1 hour
        # note: whenever emotes are refreshed (cache is saved to redis), the key is additionally set to expire
        # in one hour. This is to prevent emotes from never refreshing if the bot restarts in less than an hour.
        # (This also means that the bot will never have emotes older than 2 hours)
        ScheduleManager.execute_every(1 * 60 * 60, self.update_all_emotes)

        self.load_all_emotes()

    def update_all_emotes(self) -> None:
        self.action_queue.submit(self.bttv_emote_manager.update_all)
        self.action_queue.submit(self.ffz_emote_manager.update_all)
        self.action_queue.submit(self.seventv_emote_manager.update_all)
        self.action_queue.submit(self.twitch_emote_manager.update_all)

    def load_all_emotes(self) -> None:
        self.action_queue.submit(self.bttv_emote_manager.load_all)
        self.action_queue.submit(self.ffz_emote_manager.load_all)
        self.action_queue.submit(self.seventv_emote_manager.load_all)
        self.action_queue.submit(self.twitch_emote_manager.load_all)

    @staticmethod
    def twitch_emote_url(emote_id: str, size: str) -> str:
        return f"https://static-cdn.jtvnw.net/emoticons/v2/{emote_id}/default/dark/{size}"

    @staticmethod
    def twitch_emote(emote_id: str, code: str) -> Emote:
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
    def twitch_emote_instance(emote_id: str, code: str, start: int, end: int) -> EmoteInstance:
        return EmoteInstance(start=start, end=end, emote=EmoteManager.twitch_emote(emote_id, code))

    @staticmethod
    def parse_twitch_emotes_tag(tag, message) -> List[EmoteInstance]:
        if len(tag) <= 0:
            return []

        emote_instances: List[EmoteInstance] = []

        for emote_src in tag.split("/"):
            emote_id, emote_instances_src = emote_src.split(":")

            for emote_instance_src in emote_instances_src.split(","):
                start_src, end_src = emote_instance_src.split("-")
                start = int(start_src)
                end = int(end_src) + 1
                code = message[start:end]

                emote_instances.append(EmoteManager.twitch_emote_instance(emote_id, code, start, end))

        return emote_instances

    def match_word_to_emote(self, word: str) -> Optional[Emote]:
        emote = self.ffz_emote_manager.match_channel_emote(word)
        if emote is not None:
            return emote

        emote = self.bttv_emote_manager.match_channel_emote(word)
        if emote is not None:
            return emote

        emote = self.seventv_emote_manager.match_channel_emote(word)
        if emote is not None:
            return emote

        emote = self.ffz_emote_manager.match_global_emote(word)
        if emote is not None:
            return emote

        emote = self.bttv_emote_manager.match_global_emote(word)
        if emote is not None:
            return emote

        emote = self.seventv_emote_manager.match_global_emote(word)
        if emote is not None:
            return emote

        return None

    def parse_all_emotes(self, message: str, twitch_emotes_tag="") -> Tuple[List[EmoteInstance], EmoteInstanceCountMap]:
        # Twitch Emotes
        twitch_emote_instances = self.parse_twitch_emotes_tag(twitch_emotes_tag, message)
        twitch_emote_start_indices = {instance.start for instance in twitch_emote_instances}

        # for the other providers, split the message by spaces
        # and then, if word is not a twitch emote, consider ffz channel -> bttv channel ->
        # 7tv channel -> ffz global -> bttv global -> 7tv global in that order.
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
        seventv_global=False,
        seventv_channel=False,
    ) -> Optional[Emote]:
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
        if seventv_global:
            emotes += self.seventv_emote_manager.global_emotes
        if seventv_channel:
            emotes += self.seventv_emote_manager.channel_emotes

        if len(emotes) <= 0:
            return None

        return random.choice(emotes)


def compute_emote_counts(emote_instances: List[EmoteInstance]) -> Dict[str, EmoteInstanceCount]:
    """Turns a list of emote instances into a map mapping emote code
    to count and a list of instances."""
    emote_counts: Dict[str, EmoteInstanceCount] = {}
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
    def __init__(self) -> None:
        self.epm: Dict[str, int] = {}

        redis = RedisManager.get()
        self.redis_zadd_if_higher = redis.register_script(
            """
local c = tonumber(redis.call('zscore', KEYS[1], ARGV[1]));
if c then
    if tonumber(KEYS[2]) > c then
        redis.call('zadd', KEYS[1], KEYS[2], ARGV[1])
        return tonumber(KEYS[2]) - c
    else
        return 0
    end
else
    redis.call('zadd', KEYS[1], KEYS[2], ARGV[1])
    return 'OK'
end
"""
        )

    def handle_emotes(self, emote_counts: EmoteInstanceCountMap) -> None:
        # passed dict maps emote code (e.g. "Kappa") to an EmoteInstanceCount instance
        for emote_code, obj in emote_counts.items():
            self.epm_incr(emote_code, obj.count)

    def epm_incr(self, code: str, count: int) -> None:
        new_epm = self.epm.get(code, 0) + count
        self.epm[code] = new_epm
        self.save_epm_record(code, new_epm)
        ScheduleManager.execute_delayed(60, self.epm_decr, args=[code, count])

    def epm_decr(self, code: str, count: int) -> None:
        self.epm[code] -= count

    def save_epm_record(self, code: str, count: int) -> None:
        streamer = StreamHelper.get_streamer()
        self.redis_zadd_if_higher(keys=[f"{streamer}:emotes:epmrecord", count], args=[code])

    def get_emote_epm(self, emote_code: str) -> Optional[int]:
        """Returns the current "emote per minute" usage of the given emote code,
        or None if the emote is unknown to the bot."""
        return self.epm.get(emote_code, None)

    @staticmethod
    def get_emote_epm_record(emote_code) -> Optional[float]:
        redis = RedisManager.get()
        streamer = StreamHelper.get_streamer()
        return redis.zscore(f"{streamer}:emotes:epmrecord", emote_code)


class EcountManager:
    @staticmethod
    def handle_emotes(emote_counts: EmoteInstanceCountMap) -> None:
        # passed dict maps emote code (e.g. "Kappa") to an EmoteInstanceCount instance
        streamer = StreamHelper.get_streamer()
        redis_key = f"{streamer}:emotes:count"
        with RedisManager.pipeline_context() as redis:
            for emote_code, instance_counts in emote_counts.items():
                redis.zincrby(redis_key, instance_counts.count, emote_code)

    @staticmethod
    def get_emote_count(emote_code: str) -> Optional[int]:
        redis = RedisManager.get()
        streamer = StreamHelper.get_streamer()
        emote_count = redis.zscore(f"{streamer}:emotes:count", emote_code)
        if emote_count is None:
            return None
        return int(emote_count)
