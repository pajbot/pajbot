import datetime
import json
import logging
import urllib.parse
import urllib.request

import requests

log = logging.getLogger(__name__)


class APIBase:
    def __init__(self, strict=False):
        self.strict = strict

    def _get(self, url, headers={}):
        try:
            req = urllib.request.Request(url, None, headers)
            response = urllib.request.urlopen(req, timeout=30)
        except urllib.error.HTTPError as e:
            # If strict is True, return the proper HTTP error. Otherwise
            if self.strict:
                raise e
            else:
                return None
        except:
            log.exception('Unhandled exception in APIBase._get')
            return None

        try:
            return response.read().decode('utf-8')
        except:
            log.exception('Unhandled exception in APIBase._get while reading response')
            return None

        return None

    def _get_json(self, url, headers={}):
        data = self._get(url, headers)

        try:
            if data and type(data) is str:
                return json.loads(data)
            else:
                return data
        except:
            log.exception('Caught exception while trying to parse json data.')
            return None

        return None

    def get_url(self, endpoints=[], parameters={}, base=None):
        return (base or self.base_url) + '/'.join(endpoints) + ('' if len(parameters) == 0 else '?' + urllib.parse.urlencode(parameters))

    def getraw(self, endpoints=[], parameters={}, base=None):
        return self._get(self.get_url(endpoints, parameters, base=base), self.headers)

    def get(self, endpoints, parameters={}, base=None):
        data = self.getraw(endpoints, parameters, base=base)

        try:
            if data and type(data) is str:
                return json.loads(data)
            else:
                return data
        except:
            log.exception('Unhandled exception in APIBase.get')
            return None

        log.error('why the fuck are we here')
        return None

    def _req_with_data(self, url, data, method='POST'):
        """Send data along with the request.

        Arguments:
        url -- What url we should send the request to
        data -- Dictionary of all data we should send along with the request

        Keyword arguments:
        method -- What method we should use for the request. (default: 'POST')
        """
        try:
            encoded_data = urllib.parse.urlencode(data).encode('utf-8')
            req = urllib.request.Request(url, data=encoded_data, headers=self.headers, method=method)
            return urllib.request.urlopen(req, timeout=30)
        except urllib.error.HTTPError as e:
            # Irregular HTTP code
            if e.code in [422]:
                log.error(e)
            else:
                try:
                    error_data_raw = e.fp.read().decode('utf-8')
                    error_data = json.loads(error_data_raw)
                    log.error('HTTP Error {0}: {1}: {2}'.format(error_data['status'], error_data['error'], error_data['message']))
                except:
                    log.exception('Unhandled exception in exception handler')
            return None
        except:
            log.exception('Unhandled exception caught in method `req_with_data`')
            return None

    def post(self, endpoints=[], parameters={}, data={}, base=None):
        try:
            response = self._req_with_data(self.get_url(endpoints, parameters, base=base), data, method='POST')
            return response.read().decode('utf-8')
        except:
            log.exception('Unhandled exception caught in method `post`')
            return None

    def put(self, endpoints=[], parameters={}, data={}, base=None):
        try:
            response = self._req_with_data(self.get_url(endpoints, parameters, base=base), data, method='PUT')
            return response.read().decode('utf-8')
        except:
            log.exception('Unhandled exception caught in method `put`')
            return None


class ChatDepotAPI(APIBase):
    def __init__(self):
        APIBase.__init__(self)

        self.base_url = 'http://chatdepot.twitch.tv/'

        self.headers = {
                'Accept': 'application/vnd.twitchtv.v3+json'
                }


class ImraisingAPI(APIBase):
    def __init__(self, apikey):
        APIBase.__init__(self)

        self.base_url = 'https://imraising.tv/api/v1/'

        self.headers = {
                'Authorization': 'APIKey apikey="{0}"'.format(apikey),
                'Content-Type': 'application/json',
                }


class StreamtipAPI(APIBase):
    def __init__(self, client_id, access_token):
        APIBase.__init__(self)

        self.base_url = 'https://streamtip.com/api/'

        self.headers = {
                'Authorization': client_id + ' ' + access_token,
                }


class BTTVApi(APIBase):
    def __init__(self, strict=True):
        APIBase.__init__(self, strict)

        self.base_url = 'https://api.betterttv.net/2/'
        self.headers = {}

    def get_global_emotes(self):
        """Returns a list of global BTTV emotes in the standard Emote format."""

        emotes = []
        try:
            data = self.get(['emotes'])

            for emote in data['emotes']:
                emotes.append({'emote_hash': emote['id'], 'code': emote['code']})
        except urllib.error.HTTPError as e:
            if e.code == 502:
                log.warning('Bad Gateway when getting global emotes.')
            elif e.code == 503:
                log.warning('Service Unavailable when getting global emotes.')
            else:
                log.exception('Unhandled HTTP error code')
        except KeyError:
            log.exception('Caught exception while trying to get global BTTV emotes')
        except:
            log.exception('Uncaught exception in BTTVApi.get_global_emotes')

        return emotes

    def get_channel_emotes(self, channel):
        """Returns a list of channel-specific BTTV emotes in the standard Emote format."""

        emotes = []
        try:
            data = self.get(['channels', channel])

            for emote in data['emotes']:
                emotes.append({'emote_hash': emote['id'], 'code': emote['code']})
        except urllib.error.HTTPError as e:
            if e.code == 502:
                log.warning('Bad Gateway when getting channel emotes.')
            elif e.code == 503:
                log.warning('Service Unavailable when getting channel emotes.')
            elif e.code == 404:
                log.info('There are no BTTV Emotes for this channel.')
            else:
                log.exception('Unhandled HTTP error code')
        except KeyError:
            log.exception('Caught exception while trying to get channel-specific BTTV emotes')
        except:
            log.exception('Uncaught exception in BTTVApi.get_channel_emotes')

        return emotes


class FFZApi(APIBase):
    def __init__(self, strict=True):
        APIBase.__init__(self, strict)

        self.base_url = 'https://api.frankerfacez.com/v1/'
        self.headers = {}

    def get_global_emotes(self):
        """Returns a list of global FFZ emotes in the standard Emote format."""

        emotes = []
        try:
            data = self.get(['set', 'global'])

            for emote_set in data['sets']:
                for emote in data['sets'][emote_set]['emoticons']:
                    emotes.append({'emote_hash': emote['id'], 'code': emote['name']})
        except urllib.error.HTTPError as e:
            if e.code == 502:
                log.warning('Bad Gateway when getting global emotes.')
            elif e.code == 503:
                log.warning('Service Unavailable when getting global emotes.')
            else:
                log.exception('Unhandled HTTP error code')
        except KeyError:
            log.exception('Caught exception while trying to get global FFZ emotes')
        except:
            log.exception('Uncaught exception in FFZApi.get_global_emotes')

        return emotes

    def get_channel_emotes(self, channel):
        """Returns a list of channel-specific FFZ emotes in the standard Emote format."""

        emotes = []
        try:
            data = self.get(['room', channel])

            for emote_set in data['sets']:
                for emote in data['sets'][emote_set]['emoticons']:
                    emotes.append({'emote_hash': emote['id'], 'code': emote['name']})
        except urllib.error.HTTPError as e:
            if e.code == 502:
                log.warning('Bad Gateway when getting channel emotes.')
            elif e.code == 503:
                log.warning('Service Unavailable when getting channel emotes.')
            elif e.code == 404:
                log.info('There are no FFZ Emotes for this channel.')
            else:
                log.exception('Unhandled HTTP error code')
        except KeyError:
            log.exception('Caught exception while trying to get channel-specific FFZ emotes')
        except:
            log.exception('Uncaught exception in FFZApi.get_channel_emotes')

        return emotes


class TwitchAPI(APIBase):
    def __init__(self, client_id=None, oauth=None, strict=True):
        """
        Keyword arguments:
        client_id -- twitch api client_id
        oauth -- twitch api oauth
        strict -- Whether the APIBase object should be strict in its errors or not. (default: True)
        """
        APIBase.__init__(self, strict)

        self.base_url = 'https://api.twitch.tv/api/'
        self.kraken_url = 'https://api.twitch.tv/kraken/'
        self.tmi_url = 'https://tmi.twitch.tv/'

        self.headers = {
                'Accept': 'application/vnd.twitchtv.v3+json',
                }

        if client_id:
            self.headers['Client-ID'] = client_id
        if oauth:
            self.headers['Authorization'] = 'OAuth ' + oauth

    def parse_datetime(datetime_str):
        """Parses date strings in the format of 2015-09-11T23:01:11+00:00
        to a naive datetime object."""
        trimmed_str = datetime_str[:19]
        return datetime.datetime.strptime(trimmed_str, '%Y-%m-%dT%H:%M:%S')

    def get_subscribers(self, streamer, limit=25, offset=0, attempt=0):
        """Returns a list of subscribers within the limit+offset range.

        Arguments:
        streamer -- the streamer whose subscriber we want to fetch.

        Keyword arguments:
        limit -- Maximum number of subscribers fetched. (default: 25)
        offset - Offset for pagination. (default: 0)
        """

        if attempt > 2:
            return False, False, True
        try:
            data = self.get(['channels', streamer, 'subscriptions'], {'limit': limit, 'offset': offset}, base=self.kraken_url)
            if data:
                return [u['user']['name'] for u in data['subscriptions']], False, False
        except urllib.error.HTTPError as e:
            # Non-standard HTTP Code returned.
            log.warning('Non-standard HTTP Code returned while fetching subscribers: {0}'.format(e.code))
            log.info(e)
            log.info(e.fp.read())
        except:
            log.exception('Unhandled exception caught in TwitchAPI.get_subscribers')

        return [], attempt + 1, False

    def get_chatters(self, streamer):
        """Returns a list of chatters in the stream."""
        chatters = []

        try:
            data = self.get(['group', 'user', streamer, 'chatters'], base=self.tmi_url)
            ch = data['chatters']

            chatters = ch['moderators'] + ch['staff'] + ch['admins'] + ch['global_mods'] + ch['viewers']
        except urllib.error.HTTPError as e:
            if e.code == 502:
                log.warning('Bad Gateway when getting chatters.')
            elif e.code == 503:
                log.warning('Service Unavailable when getting chatters.')
            else:
                log.exception('Unhandled HTTP error code')
        except KeyError:
            log.exception('Caught exception while trying to get chatters for streamer {0}'.format(streamer))
        except:
            log.exception('Uncaught exception in TwitchAPI.get_chatters')

        return chatters

    def get_status(self, streamer):
        """Returns information about a user or stream on twitch.
        This method will _ALWAYS_ return a dictionary with a bunch of data.
        Check if the key 'error' is set to False to know there's some valid data in there.
        The key 'exists' is set to False if the user does not exist, True if the user exists and None if we don't know.
        """
        stream_status = {
                'error': True,
                'exists': None,
                'online': False,
                'viewers': -1,
                'game': None,
                'title': None,
                'created_at': None,
                'followers': -1,
                'views': -1,
                'broadcast_id': None,
                }
        data = None

        try:
            data = self.get(['streams', streamer], base=self.kraken_url)
            stream_status['error'] = False

            stream_status['online'] = 'stream' in data and data['stream'] is not None
            if stream_status['online']:
                stream_status['viewers'] = data['stream']['viewers']
                stream_status['game'] = data['stream']['game']
                stream_status['title'] = data['stream']['channel']['status']
                stream_status['created_at'] = data['stream']['created_at']
                stream_status['followers'] = data['stream']['channel']['followers']
                stream_status['views'] = data['stream']['channel']['views']
                stream_status['broadcast_id'] = data['stream']['_id']
        except urllib.error.HTTPError as e:
            if e.code == 404:
                stream_status['exists'] = False
                data = json.loads(e.read().decode('utf-8'))
            elif e.code == 502:
                log.warning('Bad Gateway when getting stream status.')
            elif e.code == 503:
                log.warning('Service Unavailable when getting stream status.')
            elif e.code == 422:
                # User is banned
                pass
            else:
                log.exception('Unhandled HTTP error code')
        except TypeError:
            log.warning(data)
            log.warning('Somehow, the get request returned None')
            log.exception('Something went seriously wrong during the get-request')
        except KeyError:
            log.exception('Some key in get_status does not exist. FIX!')
        except:
            log.exception('Unhandled exception in TwitchAPI.get_status')

        return stream_status

    def set_game(self, streamer, game):
        """Updates the streamers game on twitch.

        TODO: Make the method intelligent. The game we're trying to set should be
        smart enough to set the game to Counter Strike: Global Offensive if we set
        game to csgo or some other capitalization of it.

        Arguments:
        streamer -- the streamer whose game we should update (i.e. 'tyggbar')
        game -- the game we should update to (i.e. 'Counter Strike: Global Offensive')
        """
        new_game = game
        self.put(endpoints=['channels', streamer], data={'channel[game]': new_game}, base=self.kraken_url)

    def set_title(self, streamer, title):
        """Updates the streamers title on twitch.

        Arguments:
        streamer -- the streamer whose game we should update (i.e. 'tyggbar')
        title -- the title we should update to (i.e. 'Gonna play some games, yolo!')
        """
        self.put(endpoints=['channels', streamer], data={'channel[status]': title}, base=self.kraken_url)

    def get_follow_relationship(self, username, streamer):
        """Returns the follow relationship between the user and a streamer.

        Returns False if `username` is not following `streamer`.
        Otherwise, return a datetime object.

        This value is cached in Redis for 2 minutes.
        """

        # XXX TODO FIXME
        from pajbot.managers.redis import RedisManager

        redis = RedisManager.get()

        fr_key = 'fr_{username}_{streamer}'.format(username=username, streamer=streamer)
        follow_relationship = redis.get(fr_key)

        if follow_relationship is None:
            try:
                data = self.get(endpoints=['users', username, 'follows', 'channels', streamer], base=self.kraken_url)
                created_at = data['created_at']
                redis.setex(fr_key, time=120, value=created_at)
                return TwitchAPI.parse_datetime(created_at)
            except ValueError:
                raise
            except urllib.error.HTTPError:
                redis.setex(fr_key, time=120, value='-1')
                return False
            except:
                log.exception('Unhandled exception in get_follow_relationship')
                return False
        else:
            if follow_relationship == '-1':
                return False
            else:
                return TwitchAPI.parse_datetime(follow_relationship)


class SafeBrowsingAPI:
    def __init__(self, apikey, appname, appvers):
        self.apikey = apikey
        self.appname = appname
        self.appvers = appvers
        return

    def check_url(self, url):
        base_url = 'https://sb-ssl.google.com/safebrowsing/api/lookup?client=' + self.appname + '&key=' + self.apikey + '&appver=' + self.appvers + '&pver=3.1&url='
        url2 = base_url + urllib.parse.quote(url, '')
        r = requests.get(url2)

        if r.status_code == 200:
            return True  # malware or phishing

        return False  # some handling of error codes should be added, they're just ignored for now
