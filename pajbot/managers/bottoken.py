import datetime
import json
import logging

import requests

from pajbot.managers.redis import RedisManager

log = logging.getLogger(__name__)


class BotToken:
    def __init__(self, config):
        self.nickname = config['main']['nickname']
        self.client_id = config['webtwitchapi']['client_id']
        self.client_secret = config['webtwitchapi']['client_secret']

        token = RedisManager.get().get('{}:token'.format(self.nickname))
        if not token:
            raise ValueError('No token set for bot. Log into the bot using the web interface /bot_login route')

        self.token = json.loads(token)

        self.access_token_expires_at = None

    # Check if token has expired
    def expired(self):
        return self.access_token_expires_at is None or datetime.datetime.now() >= self.access_token_expires_at

    def access_token(self):
        if self.expired():
            log.debug('Bot access token has expired or was never set, refreshing it')
            try:
                payload = {
                        'grant_type': 'refresh_token',
                        'refresh_token': self.token['refresh_token'],
                        'client_id': self.client_id,
                        'client_secret': self.client_secret,
                        }
                r = requests.post('https://id.twitch.tv/oauth2/token', data=payload)
                self.token = r.json()
            except:
                log.exception('babyrate')

            RedisManager.get().set('{}:token'.format(self.nickname), r.text)
            if 'expires_in' not in self.token:
                # Infinite token
                self.token['expires_in'] = 86400
            self.access_token_expires_at = datetime.datetime.now() + datetime.timedelta(seconds=self.token['expires_in'])

        return self.token['access_token']
