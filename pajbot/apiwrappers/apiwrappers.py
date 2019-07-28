import logging
from urllib.parse import quote, urlparse, urlunparse

from requests_toolbelt.sessions import BaseUrlSession

from pajbot.bot import Bot

log = logging.getLogger(__name__)


class BaseApi:
    def __init__(self, base_url, default_headers=None):
        self.session = BaseUrlSession(base_url)

        # e.g. pajbot1/1.35
        self.session.headers["User-Agent"] = "pajbot1/{}".format(Bot.version)

        if default_headers is not None:
            self.session.headers.update(default_headers)

    @staticmethod
    def quote_path_param(param):
        return quote(param, safe="")

    def get(self, endpoint, params=None):
        response = self.session.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    def get_binary(self, endpoint, params=None):
        response = self.session.get(endpoint, params=params)
        response.raise_for_status()
        return response.content

    def post(self, endpoint, params=None, json=None):
        response = self.session.post(endpoint, params=params, json=json)
        response.raise_for_status()
        return response.json()

    def put(self, endpoint, params=None, json=None):
        response = self.session.post(endpoint, params=params, json=json)
        response.raise_for_status()
        return response.json()


def fill_in_url_scheme(url, default_scheme="https"):
    """Fill in the scheme part of a given URL string, e.g.
    with given inputs of url = "//example.com/abc" and
    default_scheme="https", the output would be
    "https://example.com/abc"

    If the given input URL already has a scheme, the scheme is not altered.
    """
    parsed_template = urlparse(url, scheme=default_scheme)
    return urlunparse(parsed_template)
