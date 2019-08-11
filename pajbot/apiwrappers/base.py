import logging
from urllib.parse import quote, urlparse, urlunparse

import datetime

from requests import Session

from pajbot import constants
from pajbot.apiwrappers.response_cache import APIResponseCache

log = logging.getLogger(__name__)


class BaseAPI:
    def __init__(self, base_url, redis=None):
        self.base_url = base_url

        self.session = Session()
        self.timeout = 20

        # e.g. pajbot1/1.35
        self.session.headers["User-Agent"] = "pajbot/{}".format(constants.VERSION)

        if redis is not None:
            self.cache = APIResponseCache(redis)

    @staticmethod
    def quote_path_param(param):
        return quote(param, safe="")

    @staticmethod
    def fill_in_url_scheme(url, default_scheme="https"):
        """Fill in the scheme part of a given URL string, e.g.
        with given inputs of url = "//example.com/abc" and
        default_scheme="https", the output would be
        "https://example.com/abc"

        If the given input URL already has a scheme, the scheme is not altered.
        """
        parsed_template = urlparse(url, scheme=default_scheme)
        return urlunparse(parsed_template)

    @staticmethod
    def parse_datetime(datetime_str):
        """Parses date strings in the format of 2015-09-11T23:01:11Z
        to a tz-aware datetime object."""
        naive_dt = datetime.datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%SZ")
        return naive_dt.replace(tzinfo=datetime.timezone.utc)

    @staticmethod
    def join_base_and_list(base, path_segments):
        url = base
        for path_segment in path_segments:
            # str(endpoint) so numbers can be used as path segments too
            url = BaseAPI.join_base_and_string(url, BaseAPI.quote_path_param(str(path_segment)))

        return url

    @staticmethod
    def join_base_and_string(base, endpoint):
        base = base.rstrip("/")
        endpoint = endpoint.lstrip("/")
        return base + "/" + endpoint

    @staticmethod
    def join_base_and_endpoint(base, endpoint):
        # For use cases with no base and absolute endpoint URLs
        if base is None:
            return endpoint

        if isinstance(endpoint, list):
            return BaseAPI.join_base_and_list(base, endpoint)
        else:
            return BaseAPI.join_base_and_string(base, endpoint)

    def request(self, method, endpoint, params, headers, json=None, **request_options):

        full_url = self.join_base_and_endpoint(self.base_url, endpoint)
        response = self.session.request(
            method, full_url, params=params, headers=headers, json=json, timeout=self.timeout, **request_options
        )
        response.raise_for_status()
        return response

    def get(self, endpoint, params=None, headers=None, **request_options):
        return self.request("GET", endpoint, params, headers, **request_options).json()

    def get_response(self, endpoint, params=None, headers=None, **request_options):
        return self.request("GET", endpoint, params, headers, **request_options)

    def get_binary(self, endpoint, params=None, headers=None, **request_options):
        return self.request("GET", endpoint, params, headers, **request_options).content

    def post(self, endpoint, params=None, headers=None, json=None, **request_options):
        return self.request("POST", endpoint, params, headers, json, **request_options).json()

    def put(self, endpoint, params=None, headers=None, json=None, **request_options):
        return self.request("PUT", endpoint, params, headers, json, **request_options).json()
