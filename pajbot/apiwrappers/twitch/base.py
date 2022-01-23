from pajbot.apiwrappers.authentication.client_credentials import ClientCredentials
from pajbot.apiwrappers.authentication.token_manager import AccessTokenManager
from pajbot.apiwrappers.base import BaseAPI

from requests import HTTPError


class BaseTwitchAPI(BaseAPI):
    authorization_header_prefix = "Bearer"

    @property
    def default_authorization(self):
        """Returns the default authorization to use if none is explicitly specified"""
        return None

    # Implements the recommended retry routine described in
    # https://dev.twitch.tv/docs/authentication/#refresh-in-response-to-server-rejection-for-bad-authentication
    # (refreshes the auth header and retries if authorization fails)
    def request(self, method, endpoint, params, headers, authorization=None, json=None):
        # authorization can be:
        #   - None (-> default will be assigned)
        #   - False (-> No Authorization)
        #   - ClientCredentials (-> Client-ID)
        #   - AccessTokenManager (-> Authorization + Client-ID)
        #   - a tuple of (ClientCredentials, AccessToken) (-> Authorization + Client-ID)

        if authorization is None:
            authorization = self.default_authorization

        if isinstance(authorization, ClientCredentials):
            auth_headers = {"Client-ID": authorization.client_id}
        elif isinstance(authorization, AccessTokenManager):
            auth_headers = {
                "Client-ID": authorization.api.client_credentials.client_id,
                "Authorization": f"{self.authorization_header_prefix} {authorization.token.access_token}",
            }
        elif isinstance(authorization, tuple):
            (client_credentials, access_token) = authorization

            auth_headers = {
                "Client-ID": client_credentials.client_id,
                "Authorization": f"{self.authorization_header_prefix} {access_token.access_token}",
            }
        else:
            auth_headers = {}

        if headers is None:
            headers = auth_headers
        else:
            headers = {**headers, **auth_headers}

        try:
            return super().request(method, endpoint, params, headers, json)
        except HTTPError as e:
            if (
                # we got a WWW-Authenticate and status 401 back
                e.response.status_code == 401
                and "WWW-Authenticate" in e.response.headers
                # and we can refresh the token
                and isinstance(authorization, AccessTokenManager)
                and authorization.can_refresh()
            ):
                # refresh...
                authorization.refresh()
                # then retry once.
                return super().request(method, endpoint, params, headers, json)
            else:
                raise e

    def get(self, endpoint, params=None, headers=None, authorization=None):
        return self.request("GET", endpoint, params, headers, authorization).json()

    def get_binary(self, endpoint, params=None, headers=None, authorization=None):
        return self.request("GET", endpoint, params, headers, authorization).content

    def post(self, endpoint, params=None, headers=None, authorization=None, json=None):
        return self.request("POST", endpoint, params, headers, authorization, json).json()

    def put(self, endpoint, params=None, headers=None, authorization=None, json=None):
        return self.request("PUT", endpoint, params, headers, authorization, json).json()

    def patch(self, endpoint, params=None, headers=None, authorization=None, json=None):
        return self.request("PATCH", endpoint, params, headers, authorization, json)
