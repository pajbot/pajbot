import logging

from json import loads as jsonify
import base64
import requests

from flask import request, session
from flask_oauthlib.client import OAuth, parse_response
from flask_oauthlib.client import OAuthRemoteApp
from flask_oauthlib.client import OAuthResponse
from flask_oauthlib.client import OAuthException

from oauthlib.common import add_params_to_uri
from flask_oauthlib.utils import to_bytes


log = logging.getLogger(__name__)


class OAuthEdited(OAuth):
    def remote_app(self, name, register=True, **kwargs):
        """Registers a new remote application.

        :param name: the name of the remote application
        :param register: whether the remote app will be registered

        Find more parameters from :class:`OAuthRemoteApp`.
        """
        remote = OAuthRemoteAppEdited(self, name, **kwargs)
        if register:
            assert name not in self.remote_apps
            self.remote_apps[name] = remote
        return remote


class OAuthRemoteAppEdited(OAuthRemoteApp):
    def request(
        self,
        url,
        data=None,
        headers=None,
        format="urlencoded",
        method="GET",
        content_type=None,
        token=None,
        discord=False,
    ):
        headers = dict(headers or {})
        if token is None:
            token = self.get_request_token()

        client = self.make_client(token)
        url = self.expand_url(url)
        if method == "GET":
            assert format == "urlencoded"
            if data:
                url = add_params_to_uri(url, data)
                data = None
        else:
            if content_type is None:
                data, content_type = OAuth.encode_request_data(data, format)
            if content_type is not None:
                headers["Content-Type"] = content_type

        if self.request_token_url:
            uri, headers, body = client.sign(url, http_method=method, body=data, headers=headers)
        else:
            uri, headers, body = client.add_token(url, http_method=method, body=data, headers=headers)

        if hasattr(self, "pre_request"):
            uri, headers, body = self.pre_request(uri, headers, body)

        if body:
            data = to_bytes(body, self.encoding)
        else:
            data = None
        if discord:
            response = requests.request(method, uri, headers=headers, data=to_bytes(body, self.encoding))
            if response.status_code not in (200, 201):
                raise OAuthException("Invalid response from %s" % self.name, type="invalid_response", data=data)
            return jsonify(response.text.encode("utf8"))

        resp, content = self.http_request(uri, headers, data=to_bytes(body, self.encoding), method=method)
        return OAuthResponse(resp, content, self.content_type)

    def authorized_response(self, args=None, spotify=False, discord=False):
        if args is None:
            args = request.args
        if spotify:
            data = self.handle_oauth2_response_spotify(args)
        elif discord:
            data = self.handle_oauth2_response_discord(args)
        else:
            if "oauth_verifier" in args:
                data = self.handle_oauth1_response(args)
            elif "code" in args:
                data = self.handle_oauth2_response(args)
            else:
                data = self.handle_unknown_response()

        session.pop("%s_oauthtok" % self.name, None)
        session.pop("%s_oauthredir" % self.name, None)
        return data

    def handle_oauth2_response_spotify(self, args):
        client = self.make_client()
        remote_args = {"code": args.get("code"), "redirect_uri": session.get("%s_oauthredir" % self.name)}
        log.debug("Prepare oauth2 remote args %r", remote_args)
        remote_args.update(self.access_token_params)
        data = f"{self._consumer_key}:{self._consumer_secret}"
        encoded = str(base64.b64encode(data.encode("utf-8")), "utf-8")
        headers = {"Authorization": f"Basic {encoded}"}
        if self.access_token_method == "POST":
            headers.update({"Content-Type": "application/x-www-form-urlencoded"})
            body = client.prepare_request_body(**remote_args)
            resp, content = self.http_request(
                self.expand_url(self.access_token_url),
                headers=headers,
                data=to_bytes(body, self.encoding),
                method=self.access_token_method,
            )
        elif self.access_token_method == "GET":
            qs = client.prepare_request_body(**remote_args)
            url = self.expand_url(self.access_token_url)
            url += ("?" in url and "&" or "?") + qs
            resp, content = self.http_request(url, headers=headers, method=self.access_token_method)
        else:
            raise OAuthException("Unsupported access_token_method: %s" % self.access_token_method)

        data = parse_response(resp, content, content_type=self.content_type)
        if resp.code not in (200, 201):
            raise OAuthException("Invalid response from %s" % self.name, type="invalid_response", data=data)
        return data
