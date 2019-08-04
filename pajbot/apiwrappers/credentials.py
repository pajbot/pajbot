import logging

import json

from pajbot.apiwrappers.authentication.access_token import AccessToken

log = logging.Logger(__name__)


class TwitchCredentialsProvider:
    def __init__(self, redis, twitch_id_api, client_id, client_secret, bot_access_token, bot_user_id):
        self.redis = redis
        self.twitch_id_api = twitch_id_api
        self.client_id = client_id
        self.client_secret = client_secret

        # if present/specified by the bot operator, a infinitely-lived access token for the bot
        # user to use instead of the refreshable token stored in redis
        self.bot_access_token = bot_access_token

        self.bot_user_id = bot_user_id
        self.redis_key = "{}:token".format(self.bot_user_id)

    def app_authorization(self):
        token = self.twitch_id_api.get_app_access_token(self.client_id, self.client_secret)
        return token.access_token

    def bot_authorization(self):
        cache_result = self.redis.get(self.redis_key)

        if cache_result is None:
            raise ValueError("No token set for bot. Log into the bot using the web interface /bot_login route")

        token = AccessToken.from_json(json.loads(cache_result))

        if token.should_refresh():
            # get a new token using the refresh token from the previous one
            log.debug("Refreshing bot token")

            token = self.twitch_id_api.refresh_user_access_token(
                self.client_id, self.client_secret, token.refresh_token
            )
            self.redis.set(self.redis_key, json.dumps(token.jsonify()))

        return token.access_token
