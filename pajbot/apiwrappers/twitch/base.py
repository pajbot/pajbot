from requests import HTTPError

from pajbot.apiwrappers.authentication.access_token import AccessToken
from pajbot.apiwrappers.authentication.client_credentials import ClientCredentials
from pajbot.apiwrappers.authentication.token_manager import AccessTokenManager
from pajbot.apiwrappers.base import BaseAPI


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
        #   - AccessTokenManager (-> Authorization)
        #   - AccessToken (-> Authorization)

        if authorization is None:
            authorization = self.default_authorization

        if isinstance(authorization, ClientCredentials):
            auth_headers = {"Client-ID": authorization.client_id}
        elif isinstance(authorization, AccessTokenManager):
            auth_headers = {
                "Authorization": "{} {}".format(self.authorization_header_prefix, authorization.token.access_token)
            }
        elif isinstance(authorization, AccessToken):
            auth_headers = {
                "Authorization": "{} {}".format(self.authorization_header_prefix, authorization.access_token)
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
            if not (
                # we got a WWW-Authenticate and status 401 back
                e.response.status_code == 401
                and "WWW-Authenticate" in e.response.headers
                # and we can refresh the token
                and isinstance(authorization, AccessTokenManager)
                and authorization.can_refresh()
            ):
                raise e

            # refresh...
            authorization.refresh()

            # then retry once.
            return super().request(method, endpoint, params, headers, json)

    def get(self, endpoint, params=None, headers=None, authorization=None):
        return self.request("GET", endpoint, params, headers, authorization).json()

    def get_binary(self, endpoint, params=None, headers=None, authorization=None):
        return self.request("GET", endpoint, params, headers, authorization).content

    def post(self, endpoint, params=None, headers=None, authorization=None, json=None):
        return self.request("POST", endpoint, params, headers, authorization, json).json()

    def put(self, endpoint, params=None, headers=None, authorization=None, json=None):
        return self.request("PUT", endpoint, params, headers, authorization, json).json()
