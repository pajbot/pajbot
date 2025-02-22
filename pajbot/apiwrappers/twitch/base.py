import asyncio
from typing import Any
from pajbot.apiwrappers.authentication.client_credentials import ClientCredentials
from pajbot.apiwrappers.authentication.token_manager import AccessTokenManager
from pajbot.apiwrappers.base import AnyEndpoint, BaseAPI

from requests import HTTPError, Response


class BaseTwitchAPI(BaseAPI):
    authorization_header_prefix = "Bearer"

    @property
    def default_authorization(self):
        """Returns the default authorization to use if none is explicitly specified"""
        return None

    # Implements the recommended retry routine described in
    # https://dev.twitch.tv/docs/authentication/#refresh-in-response-to-server-rejection-for-bad-authentication
    # (refreshes the auth header and retries if authorization fails)
    async def request(
        self,
        method: str,
        endpoint: AnyEndpoint,
        params: Any,
        headers: Any,
        authorization=None,
        json=None,
    ) -> Response:
        loop = asyncio.get_event_loop()

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
            response = await super()._request(method, endpoint, params, headers, json)
            return response
        except HTTPError as e:
            if e.response is None:
                raise e

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
                response = await super()._request(method, endpoint, params, headers, json)
                return response
            else:
                raise e

    async def get(
        self,
        endpoint: AnyEndpoint,
        params=None,
        headers=None,
        authorization=None,
    ) -> dict[str, Any]:
        response = await self.request("GET", endpoint, params, headers, authorization)
        return response.json()

    async def get_binary(
        self,
        endpoint,
        params=None,
        headers=None,
        authorization=None,
    ):
        response = await self.request("GET", endpoint, params, headers, authorization)
        return response.content

    async def post(
        self,
        endpoint,
        params=None,
        headers=None,
        authorization=None,
        json=None,
    ):
        response = await self.request("POST", endpoint, params, headers, authorization, json)
        return response.json()

    async def post_204(self, endpoint, params=None, headers=None, authorization=None, json=None) -> Response:
        """
        Send a POST request to an endpoint where we expect no content from it, so no parsing
        is done on the response.

        This method returns the response object
        """
        return await self.request("POST", endpoint, params, headers, authorization, json)

    def put(self, endpoint, params=None, headers=None, authorization=None, json=None):
        return self.request("PUT", endpoint, params, headers, authorization, json).json()

    def patch(self, endpoint, params=None, headers=None, authorization=None, json=None):
        return self.request("PATCH", endpoint, params, headers, authorization, json)

    def delete(self, endpoint, params=None, headers=None, authorization=None, json=None):
        return self.request("DELETE", endpoint, params, headers, authorization, json)
