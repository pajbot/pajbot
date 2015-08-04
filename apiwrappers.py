import urllib.parse
import urllib.request
import json
import logging
import requests

log = logging.getLogger('tyggbot')


class APIBase:
    @staticmethod
    def _get(url, headers={}):
        try:
            req = urllib.request.Request(url, None, headers)
            response = urllib.request.urlopen(req)
        except Exception as e:
            return None

        try:
            return response.read().decode('utf-8')
        except Exception as e:
            log.error(e)
            return None

        return None

    @staticmethod
    def _get_json(url, headers={}):
        try:
            data = APIBase._get(url, headers)
            if data:
                return json.loads(data)
            else:
                return data
        except Exception:
            log.exception('Caught exception while trying to parse json data.')
            return None

        return None

    def get_url(self, endpoints=[], parameters={}):
        return self.base_url + '/'.join(endpoints) + ('' if len(parameters) == 0 else '?' + urllib.parse.urlencode(parameters))

    def getraw(self, endpoints=[], parameters={}):
        return APIBase._get(self.get_url(endpoints, parameters), self.headers)

    def get(self, endpoints, parameters={}):
        try:
            data = self.getraw(endpoints, parameters)
            if data:
                return json.loads(data)
            else:
                return data
        except Exception as e:
            log.error(e)
            return None

        return None

    def post(self, endpoints=[], parameters={}, data={}):
        try:
            req = urllib.request.Request(self.get_url(endpoints, parameters), urllib.parse.urlencode(data).encode('utf-8'), self.headers)
            response = urllib.request.urlopen(req)
        except Exception as e:
            log.error(e)
            return None

        try:
            return response.read().decode('utf-8')
        except Exception as e:
            log.error(e)
            return None

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
    def __init__(self, client_id=None, oauth=None, type='kraken'):
        APIBase.__init__(self)

        self.base_url = 'https://api.twitch.tv/{0}/'.format(type)

        self.headers = {
                'Accept': 'application/vnd.twitchtv.v3+json',
                }

        if client_id:
            self.headers['Client-ID'] = client_id
        if oauth:
            self.headers['Authorization'] = 'OAuth ' + oauth


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
