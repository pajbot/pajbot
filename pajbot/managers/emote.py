import datetime
import json
import logging
import os
import re

import requests

from pajbot.apiwrappers import APIBase
from pajbot.managers.redis import RedisManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.streamhelper import StreamHelper

log = logging.getLogger(__name__)


class BTTVEmoteManager:
    def __init__(self):
        from pajbot.apiwrappers import BTTVApi
        self.api = BTTVApi()
        self.global_emotes = []
        streamer = StreamHelper.get_streamer()
        _global_emotes = RedisManager.get().hgetall('global:emotes:bttv')
        try:
            _channel_emotes = RedisManager.get().hgetall('{streamer}:emotes:bttv_channel_emotes'.format(streamer=streamer))
        except:
            _channel_emotes = {}

        self.channel_emotes = list(_channel_emotes.keys())

        _all_emotes = _global_emotes.copy()
        _all_emotes.update(_channel_emotes)

        self.all_emotes = []
        for emote_code, emote_hash in _all_emotes.items():
            self.all_emotes.append(self.build_emote(emote_code, emote_hash))

    def build_emote(self, emote_code, emote_hash):
        return {
                'code': emote_code,
                'type': 'bttv',
                'emote_hash': emote_hash,
                'regex': re.compile('(?<![^ ]){0}(?![^ ])'.format(re.escape(emote_code))),
                }

    def update_emotes(self):
        log.debug('Updating BTTV Emotes...')
        global_emotes = self.api.get_global_emotes()
        channel_emotes = self.api.get_channel_emotes(StreamHelper.get_streamer())

        self.global_emotes = [emote['code'] for emote in global_emotes]
        self.channel_emotes = [emote['code'] for emote in channel_emotes]

        # Store channel emotes in redis
        streamer = StreamHelper.get_streamer()
        key = '{streamer}:emotes:bttv_channel_emotes'.format(streamer=streamer)
        with RedisManager.pipeline_context() as pipeline:
            pipeline.delete(key)
            for emote in channel_emotes:
                pipeline.hset(key, emote['code'], emote['emote_hash'])

        self.all_emotes = []
        with RedisManager.pipeline_context() as pipeline:
            for emote in global_emotes + channel_emotes:
                # Store all possible emotes, with their regex in an easily
                # accessible list.
                self.all_emotes.append(self.build_emote(emote['code'], emote['emote_hash']))

                # Make sure all available emotes are available in redis
                pipeline.hset('global:emotes:bttv', emote['code'], emote['emote_hash'])


class FFZEmoteManager:
    def __init__(self):
        from pajbot.apiwrappers import FFZApi
        self.api = FFZApi()
        self.global_emotes = []
        streamer = StreamHelper.get_streamer()

        # Try to get the list of global emotes from redis
        _global_emotes = RedisManager.get().hgetall('global:emotes:ffz')
        try:
            _channel_emotes = RedisManager.get().hgetall('{streamer}:emotes:ffz_channel_emotes'.format(streamer=streamer))
        except:
            _channel_emotes = {}

        self.channel_emotes = list(_channel_emotes.keys())

        _all_emotes = _global_emotes.copy()
        _all_emotes.update(_channel_emotes)

        self.all_emotes = []
        for emote_code, emote_hash in _all_emotes.items():
            self.all_emotes.append(self.build_emote(emote_code, emote_hash))

    def build_emote(self, emote_code, emote_hash):
        return {
                'code': emote_code,
                'type': 'ffz',
                'emote_id': emote_hash,
                'regex': re.compile('(?<![^ ]){0}(?![^ ])'.format(re.escape(emote_code))),
                }

    def update_emotes(self):
        log.debug('Updating FFZ Emotes...')
        global_emotes = self.api.get_global_emotes()
        channel_emotes = self.api.get_channel_emotes(StreamHelper.get_streamer())

        self.global_emotes = [emote['code'] for emote in global_emotes]
        self.channel_emotes = [emote['code'] for emote in channel_emotes]

        # Store channel emotes in redis
        streamer = StreamHelper.get_streamer()
        key = '{streamer}:emotes:ffz_channel_emotes'.format(streamer=streamer)
        with RedisManager.pipeline_context() as pipeline:
            pipeline.delete(key)
            for emote in channel_emotes:
                pipeline.hset(key, emote['code'], emote['emote_hash'])

        self.all_emotes = []
        with RedisManager.pipeline_context() as pipeline:
            for emote in global_emotes + channel_emotes:
                # Store all possible emotes, with their regex in an easily
                # accessible list.
                self.all_emotes.append(self.build_emote(emote['code'], emote['emote_hash']))

                # Make sure all available emotes are available in redis
                pipeline.hset('global:emotes:ffz', emote['code'], emote['emote_hash'])


class EmoteManager:
    def __init__(self, bot):
        # this should probably not even be a dictionary
        self.bot = bot
        self.streamer = bot.streamer
        self.bttv_emote_manager = BTTVEmoteManager()
        self.ffz_emote_manager = FFZEmoteManager()
        redis = RedisManager.get()
        self.subemotes = redis.hgetall('global:emotes:twitch_subemotes')

        # Emote current EPM
        self.epm = {}

        try:
            # Update BTTV Emotes every 2 hours
            ScheduleManager.execute_every(60 * 60 * 2, self.bttv_emote_manager.update_emotes)

            # Update Twitch emotes every 3 hours
            ScheduleManager.execute_every(60 * 60 * 3, self.update_emotes)
        except:
            pass

        # Used as caching to store emotes
        self.global_emotes = []

    def find(self, key):
        log.info('Finding emote with key {0}'.format(key))
        try:
            emote_id = int(key)
        except ValueError:
            emote_id = None

        if emote_id:
            return self.data[emote_id]
        else:
            key = str(key)
            if len(key) > 0 and key[0] == ':':
                key = key.upper()
            if key in self.data:
                return self.data[key]

        return None

    def update_emotes(self):
        base_url = 'https://twitchemotes.com/api_cache/v2/{0}.json'
        endpoints = [
                'global',
                'subscriber',
                ]

        twitch_emotes = {}
        twitch_subemotes = {}

        for endpoint in endpoints:
            log.debug('Refreshing {0} emotes...'.format(endpoint))
            data = requests.get(base_url.format(endpoint)).json()

            if 'channels' in data:
                for channel in data['channels']:
                    chan = data['channels'][channel]
                    # chan_id = chan['id']
                    emotes = chan['emotes']

                    emote_codes = []
                    pending_emotes = []

                    for emote in emotes:
                        emote_codes.append(emote['code'])
                        pending_emotes.append(emote)

                    prefix = os.path.commonprefix(emote_codes)
                    if len(prefix) > 1 and ''.join(filter(lambda c: c.isalpha(), prefix)).islower():
                        for emote in pending_emotes:
                            twitch_emotes[emote['code']] = emote['image_id']
                            twitch_subemotes[emote['code']] = channel
            else:
                for code, emote_data in data['emotes'].items():
                    twitch_emotes[code] = emote_data['image_id']

        with RedisManager.pipeline_context() as pipeline:
            pipeline.delete('global:emotes:twitch_subemotes')
            pipeline.hmset('global:emotes:twitch', twitch_emotes)
            pipeline.hmset('global:emotes:twitch_subemotes', twitch_subemotes)

        self.subemotes = twitch_subemotes

    def get_global_emotes(self, force=False):
        if len(self.global_emotes) > 0 or force is True:
            return self.global_emotes

        """Returns a list of global twitch emotes"""
        base_url = 'http://twitchemotes.com/api_cache/v2/global.json'
        log.info('Getting global twitch emotes!')
        try:
            api = APIBase()
            message = json.loads(api._get(base_url))
        except ValueError:
            log.error('Invalid data fetched while getting global emotes!')
            return False

        for code in message['emotes']:
            self.global_emotes.append(code)

        return self.global_emotes

    def get_global_bttv_emotes(self):
        emotes_full_list = self.bttv_emote_manager.global_emotes
        emotes_remove_list = ['aplis!', 'Blackappa', 'DogeWitIt', 'BadAss', 'Kaged', '(chompy)', 'SoSerious', 'BatKappa', 'motnahP']

        return list(set(emotes_full_list) - set(emotes_remove_list))

    def parse_message_twitch_emotes(self, source, message, tag, whisper):
        message_emotes = []
        new_user_tags = []

        # Twitch Emotes
        if tag:
            emote_data = tag.split('/')
            for emote in emote_data:
                try:
                    emote_id, emote_occurrences = emote.split(':')
                    emote_indices = emote_occurrences.split(',')

                    # figure out how many times the emote occured in the message
                    emote_count = len(emote_indices)

                    first_index, last_index = emote_indices[0].split('-')
                    first_index = int(first_index)
                    last_index = int(last_index)
                    emote_code = message[first_index:last_index + 1]
                    if emote_code[0] == ':':
                        emote_code = emote_code.upper()
                    message_emotes.append({
                        'code': emote_code,
                        'twitch_id': emote_id,
                        'start': first_index,
                        'end': last_index,
                        'count': emote_count,
                        })

                    sub = self.subemotes.get(emote_code, None)
                    if sub:
                        new_user_tags.append('{sub}_sub'.format(sub=sub))
                except:
                    log.exception('Exception caught while splitting emote data')
                    log.error('Emote data: {}'.format(emote_data))
                    log.error('Message: {}'.format(message))

        # BTTV Emotes
        for emote in self.bttv_emote_manager.all_emotes:
            num = 0
            start = -1
            end = -1
            for match in emote['regex'].finditer(message):
                num += 1
                if num == 1:
                    start = match.span()[0]
                    end = match.span()[1] - 1  # don't ask me
            if num > 0:
                message_emotes.append({
                    'code': emote['code'],
                    'bttv_hash': emote['emote_hash'],
                    'start': start,
                    'end': end,
                    'count': num,
                    })

        # FFZ Emotes
        for emote in self.ffz_emote_manager.all_emotes:
            num = 0
            start = -1
            end = -1
            for match in emote['regex'].finditer(message):
                num += 1
                if num == 1:
                    start = match.span()[0]
                    end = match.span()[1] - 1  # don't ask me
            if num > 0:
                message_emotes.append({
                    'code': emote['code'],
                    'ffz_id': emote['emote_id'],
                    'start': start,
                    'end': end,
                    'count': num,
                    })

        if len(message_emotes) > 0 or len(new_user_tags) > 0:
            streamer = StreamHelper.get_streamer()
            with RedisManager.pipeline_context() as pipeline:
                if not whisper:
                    for emote in message_emotes:
                        pipeline.zincrby('{streamer}:emotes:count'.format(streamer=streamer), emote['code'], emote['count'])
                        self.epm_incr(emote['code'], emote['count'])

                user_tags = source.get_tags()

                for tag in new_user_tags:
                    user_tags[tag] = (datetime.datetime.now() + datetime.timedelta(days=15)).timestamp()
                source.set_tags(user_tags, redis=pipeline)

        return message_emotes

    def epm_incr(self, code, count):
        if code in self.epm:
            self.epm[code] += count
        else:
            self.epm[code] = count
        ScheduleManager.execute_delayed(60, self.epm_decr, args=[code, count])

    def epm_decr(self, code, count):
        self.epm[code] -= count

    def get_emote_count(self, emote_code):
        redis = RedisManager.get()
        streamer = StreamHelper.get_streamer()

        emote_count = redis.zscore('{streamer}:emotes:count'.format(streamer=streamer), emote_code)
        if emote_count:
            return int(emote_count)
        return None

    def get_emote_epm(self, emote_code):
        return self.epm.get(emote_code, None)

    def get_emote_epmrecord(self, emote_code):
        redis = RedisManager.get()
        streamer = StreamHelper.get_streamer()

        emote_count = redis.zscore('{streamer}:emotes:epmrecord'.format(streamer=streamer), emote_code)
        if emote_count:
            return int(emote_count)
        return None
