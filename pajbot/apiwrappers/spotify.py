import logging
import base64
from json.decoder import JSONDecodeError

from pajbot.apiwrappers.base import BaseAPI
from pajbot.apiwrappers.authentication.token_manager import UserAccessTokenManager
from pajbot.apiwrappers.authentication.access_token import UserAccessToken

log = logging.getLogger(__name__)


class SpotifyPlayerAPI(BaseAPI):
    def __init__(self, redis):
        super().__init__(base_url="https://api.spotify.com/v1/", redis=redis)
        self.device_id = None

    def authentication(self, authentication):
        if isinstance(authentication, UserAccessTokenManager):
            return {"Authorization": "Bearer " + str(authentication.token.access_token)}
        elif isinstance(authentication, UserAccessToken):
            return {"Authorization": "Bearer " + str(authentication.access_token)}
        elif isinstance(authentication, str):
            return {"Authorization": f"Bearer {authentication}"}
        return {}

    def pause(self, authentication):
        headers = self.authentication(authentication)
        if not headers:
            return False

        if not self.device_id:
            self.state(authentication)
        if not self.device_id:
            return False

        try:
            self.put(endpoint="me/player", headers=headers, json={"device_ids": [self.device_id], "play": False})
        except JSONDecodeError:
            pass

        return True

    def play(self, authentication):
        headers = self.authentication(authentication)
        if not headers:
            return False

        if not self.device_id:
            self.state(authentication)
        if not self.device_id:
            return False

        try:
            self.put(endpoint="me/player", headers=headers, json={"device_ids": [self.device_id], "play": True})
        except JSONDecodeError:
            pass

        return True

    def state(self, authentication):
        headers = self.authentication(authentication)
        if not headers:
            return None, None, None

        try:
            data = self.get(endpoint="me/player", headers=headers)
        except JSONDecodeError:
            return False, None, None

        self.device_id = data["device"]["id"]
        artists = []

        for artist in data["item"]["artists"]:
            artists.append(artist["name"])

        return data["is_playing"], data["item"]["name"], artists

    def get_user_data(self, authentication):
        headers = self.authentication(authentication)
        if not headers:
            return False

        return self.get("me", headers=headers)


class SpotifyTokenAPI(BaseAPI):
    def __init__(self, redis, client_id, client_secret, redirect_uri):
        super().__init__(base_url="https://accounts.spotify.com", redis=redis)
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    @property
    def authentication(self):
        return {
            "Authorization": "Basic "
            + str(base64.b64encode(f"{self.client_id}:{self.client_secret}".encode("utf-8")), "utf-8")
        }

    def get_user_access_token(self, code):
        headers = self.authentication
        data = {"grant_type": "authorization_code", "code": code, "redirect_uri": self.redirect_uri}
        response = self.post("/api/token", data=data, headers=headers)

        # {
        # "access_token": "NgCXRK...MzYjw",
        # "token_type": "Bearer",
        # "scope": "user-read-playback-state user-modify-playback-state user-read-currently-playing user-read-email user-read-private",
        # "expires_in": 3600,
        # "refresh_token": "NgAagA...Um_SHo"
        # }
        log.info("Recieved token")
        return UserAccessToken.from_api_response(response)

    def refresh_user_access_token(self, refresh_token):
        headers = self.authentication
        data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
        response = self.post("/api/token", data=data, headers=headers)

        # {
        # "access_token": "NgA6ZcYI...ixn8bUQ",
        # "token_type": "Bearer",
        # "scope": "user-read-playback-state user-modify-playback-state user-read-currently-playing user-read-email user-read-private",
        # "expires_in": 3600
        # }
        if "refresh_token" not in response:
            response["refresh_token"] = refresh_token
        log.info("Refreshed spotify token")
        return UserAccessToken.from_api_response(response)
