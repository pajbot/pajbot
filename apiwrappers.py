import urllib.parse
import urllib.request
import json
import logging
import requests

log = logging.getLogger('tyggbot')


class APIBase:
    def __init__(self, strict=False):
        self.strict = strict

    def _get(self, url, headers={}):
        log.info(url)
        try:
            req = urllib.request.Request(url, None, headers)
            response = urllib.request.urlopen(req)
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
            return urllib.request.urlopen(req)
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

        self.headers = {
                'Accept': 'application/vnd.twitchtv.v3+json',
                }

        if client_id:
            self.headers['Client-ID'] = client_id
        if oauth:
            self.headers['Authorization'] = 'OAuth ' + oauth

    def get_subscribers(self, streamer, limit=25, offset=0):
        """Returns a list of subscribers within the limit+offset range.

        Arguments:
        streamer -- the streamer whose subscriber we want to fetch.

        Keyword arguments:
        limit -- Maximum number of subscribers fetched. (default: 25)
        offset - Offset for pagination. (default: 0)
        """
        try:
            data = self.get(['channels', streamer, 'subscriptions'], {'limit': limit, 'offset': offset}, base='https://api.twitch.tv/kraken/')
            log.info(data)
            if data:
                return data['subscriptions']
        except urllib.error.HTTPError as e:
            # Non-standard HTTP Code returned.
            log.warning('Non-standard HTTP Code returned while fetching subscribers: {0}'.format(e.code))
            log.info(e)
            log.info(e.fp.read())
            return []
        except:
            log.exception('Unhandled exception caught in TwitchAPI.get_subscribers')
            return []

    def get_chatters(self, streamer):
        """Returns a list of chatters in the stream."""
        chatters = []

        try:
            data = self.get(['group', 'user', streamer, 'chatters'], base='https://tmi.twitch.tv/')
            ch = data['chatters']

            chatters = ch['moderators'] + ch['staff'] + ch['admins'] + ch['global_mods'] + ch['viewers']
        except KeyError:
            log.exception('Caught exception while trying to get chatters for streamer {0}'.format(streamer))
        except:
            log.exception('Uncaught exception in TwitchAPI.get_chatters')

        return chatters

    def get_status(self, streamer):
        data = self.get(['streams', streamer], base='https://api.twitch.tv/kraken/')
        ret = {
                'error': True,
                'online': False,
                'viewers': -1,
                'game': None,
                'title': None,
                'created_at': None,
                'followers': -1,
                'views': -1,
                }
        if data:
            try:
                ret['online'] = 'stream' in data and data['stream'] is not None
                if ret['online']:
                    ret['viewers'] = data['stream']['viewers']
                    ret['game'] = data['stream']['game']
                    ret['title'] = data['stream']['channel']['status']
                    ret['created_at'] = data['stream']['created_at']
                    ret['followers'] = data['stream']['channel']['followers']
                    ret['views'] = data['stream']['channel']['views']
                ret['error'] = False
            except:
                log.exception('Exception caught while getting stream status')

        return ret

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
        self.put(endpoints=['channels', streamer], data={'channel[game]': new_game}, base='https://api.twitch.tv/kraken/')

    def set_title(self, streamer, title):
        """Updates the streamers title on twitch.

        Arguments:
        streamer -- the streamer whose game we should update (i.e. 'tyggbar')
        title -- the title we should update to (i.e. 'Gonna play some games, yolo!')
        """
        self.put(endpoints=['channels', streamer], data={'channel[status]': title}, base='https://api.twitch.tv/kraken/')


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
