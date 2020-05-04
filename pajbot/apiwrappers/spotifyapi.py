import logging
import base64

from pajbot.apiwrappers.base import BaseAPI
from pajbot.apiwrappers.authentication.access_token import SpotifyAccessToken

log = logging.getLogger(__name__)


class SpotifyApi(BaseAPI):
    def __init__(self, redis, client_id, client_secret, redirect_uri):
        super().__init__(base_url="https://api.spotify.com/v1/", redis=redis)
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.device_id = None

    def pause(self, token_manager):
        if token_manager.token is None:
            log.error("Spotify user id is not correct!")
            return None

        headers = {"Authorization": "Bearer " + str(token_manager.token.access_token)}
        if token_manager.token.access_token is None:
            return False

        if not self.device_id:
            self.state(token_manager)
        if not self.device_id:
            return False
        self.put(endpoint="me/player", headers=headers, json={"device_ids": [f"{self.device_id}"], "play": False})

    def play(self, token_manager):
        if token_manager.token is None:
            log.error("Spotify user id is not correct!")
            return None

        headers = {"Authorization": "Bearer " + str(token_manager.token.access_token)}
        if token_manager.token.access_token is None:
            return False

        if not self.device_id:
            self.state(token_manager)
        if not self.device_id:
            return False

        self.put(endpoint="me/player", headers=headers, json={"device_ids": [f"{self.device_id}"], "play": True})

    def state(self, token_manager):
        if token_manager.token is None:
            log.error("Spotify user id is not correct!")
            return tuple([False, None, None])
        headers = {"Authorization": "Bearer " + str(token_manager.token.access_token)}
        if token_manager.token.access_token is None:
            return tuple([False, None, None])
        data = self.get(endpoint="me/player", headers=headers)
        if data is None:
            return tuple([False, None, None])
        self.device_id = data["device"]["id"]
        artists = []

        for artist in data["item"]["artists"]:
            artists.append(artist["name"])

        return tuple([data["is_playing"], data["item"]["name"], artists])

    def get_user_access_token(self, code):
        headers = {
            "Authorization": "Basic "
            + str(base64.b64encode(f"{self.client_id}:{self.client_secret}".encode("utf-8")), "utf-8")
        }
        data = {"grant_type": "authorization_code", "code": code, "redirect_uri": self.redirect_uri}
        response = self.post("/api/token", data=data, headers=headers, base_url="https://accounts.spotify.com")

        # {
        # "access_token": "NgCXRK...MzYjw",
        # "token_type": "Bearer",
        # "scope": "user-read-playback-state user-modify-playback-state user-read-currently-playing user-read-email user-read-private",
        # "expires_in": 3600,
        # "refresh_token": "NgAagA...Um_SHo"
        # }
        log.info("Recieved token")
        return SpotifyAccessToken.from_api_response(response)

    def refresh_user_access_token(self, refresh_token):
        headers = {
            "Authorization": "Basic "
            + str(base64.b64encode(f"{self.client_id}:{self.client_secret}".encode("utf-8")), "utf-8")
        }
        data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
        response = self.post("/api/token", data=data, headers=headers, base_url="https://accounts.spotify.com")

        # {
        # "access_token": "NgA6ZcYI...ixn8bUQ",
        # "token_type": "Bearer",
        # "scope": "user-read-playback-state user-modify-playback-state user-read-currently-playing user-read-email user-read-private",
        # "expires_in": 3600
        # }
        if "refresh_token" not in response:
            response["refresh_token"] = refresh_token
        log.info("Refreshed spotify token")
        return SpotifyAccessToken.from_api_response(response)
