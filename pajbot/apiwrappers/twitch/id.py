from pajbot.apiwrappers.authentication.access_token import AppAccessToken, UserAccessToken
from pajbot.apiwrappers.authentication.client_credentials import ClientCredentials
from pajbot.apiwrappers.base import BaseAPI


class TwitchIDAPI(BaseAPI):
    def __init__(self, client_credentials: ClientCredentials) -> None:
        super().__init__(base_url="https://id.twitch.tv")
        self.client_credentials = client_credentials

    def get_client_credentials(self) -> ClientCredentials:
        return self.client_credentials

    async def get_app_access_token(self, scope: list[str] = []) -> AppAccessToken:
        response = await self._post(
            "/oauth2/token",
            {
                "client_id": self.client_credentials.client_id,
                "client_secret": self.client_credentials.client_secret,
                "grant_type": "client_credentials",
                "scope": (" ".join(scope)),
            },
        )

        # response =
        # {
        #   "access_token": "xxxxxxxxxxxxxxxxxxxxxxxxx",
        #   "expires_in": 5350604,
        #   "token_type": "bearer"
        # }

        return AppAccessToken.from_api_response(response)

    async def get_user_access_token(self, code: str) -> UserAccessToken:
        response = await self._post(
            "/oauth2/token",
            {
                "client_id": self.client_credentials.client_id,
                "client_secret": self.client_credentials.client_secret,
                "code": code,
                "redirect_uri": self.client_credentials.redirect_uri,
                "grant_type": "authorization_code",
            },
        )

        # response =
        # {
        #   "access_token": "xxxxxxxxxxxxxxxxxxxxxxxxxxx"
        #   "expires_in": 14310,
        #   "refresh_token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        #   "scope": [
        #     "user:read:email"
        #   ],
        #   "token_type": "bearer"
        # }

        return UserAccessToken.from_api_response(response)

    async def refresh_user_access_token(self, refresh_token):
        response = await self._post(
            "/oauth2/token",
            {
                "client_id": self.client_credentials.client_id,
                "client_secret": self.client_credentials.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )

        # response =
        # {
        #   "access_token": "xxxxxxxxxxxxxxxxxxxxxxxxxxx",
        #   "expires_in": 14346,
        #   "refresh_token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        #   "scope": [
        #     "user:read:email"
        #   ],
        #   "token_type": "bearer"
        # }

        return UserAccessToken.from_api_response(response)
