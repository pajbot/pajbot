from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Union

import datetime
import logging
from urllib.parse import quote, urlparse, urlunparse

from pajbot import constants
from pajbot.apiwrappers.response_cache import APIResponseCache

from requests import Session, Response

if TYPE_CHECKING:
    from pajbot.managers.redis import RedisType

AnyEndpoint = Union[List[Any], str]

log = logging.getLogger(__name__)


class BaseAPI:
    def __init__(self, base_url: Optional[str], redis: Optional[RedisType] = None) -> None:
        self.base_url = base_url

        self.session = Session()
        self.timeout = 20

        # e.g. pajbot1/1.35
        self.session.headers["User-Agent"] = f"pajbot/{constants.VERSION}"

        if redis is not None:
            self.cache = APIResponseCache(redis)

    @staticmethod
    def quote_path_param(param: str) -> str:
        return quote(param, safe="")

    @staticmethod
    def fill_in_url_scheme(url: str, default_scheme: str = "https") -> str:
        """Fill in the scheme part of a given URL string, e.g.
        with given inputs of url = "//example.com/abc" and
        default_scheme="https", the output would be
        "https://example.com/abc"

        If the given input URL already has a scheme, the scheme is not altered.
        """
        parsed_template = urlparse(url, scheme=default_scheme)
        return urlunparse(parsed_template)

    @staticmethod
    def parse_datetime(datetime_str: str) -> datetime.datetime:
        """Parses date strings in the format of 2015-09-11T23:01:11Z
        to a tz-aware datetime object."""
        naive_dt = datetime.datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%SZ")
        return naive_dt.replace(tzinfo=datetime.timezone.utc)

    @staticmethod
    def join_base_and_list(base: str, path_segments: List[Any]) -> str:
        url = base
        for path_segment in path_segments:
            # str(endpoint) so numbers can be used as path segments too
            url = BaseAPI.join_base_and_string(url, BaseAPI.quote_path_param(str(path_segment)))

        return url

    @staticmethod
    def join_base_and_string(base: str, endpoint: str) -> str:
        base = base.rstrip("/")
        endpoint = endpoint.lstrip("/")
        return base + "/" + endpoint

    @staticmethod
    def join_base_and_endpoint(base: Optional[str], endpoint: AnyEndpoint) -> str:
        # For use cases with no base and absolute endpoint URLs
        if base is None:
            return str(endpoint)

        if isinstance(endpoint, list):
            return BaseAPI.join_base_and_list(base, endpoint)
        else:
            return BaseAPI.join_base_and_string(base, endpoint)

    def request(
        self,
        method: str,
        endpoint: AnyEndpoint,
        params: Any,
        headers: Any,
        json: Optional[Any] = None,
        **request_options: Any,
    ) -> Response:
        full_url = self.join_base_and_endpoint(self.base_url, endpoint)
        response = self.session.request(
            method, full_url, params=params, headers=headers, json=json, timeout=self.timeout, **request_options
        )
        response.raise_for_status()
        return response

    def get(self, endpoint: AnyEndpoint, params: Any = None, headers: Any = None, **request_options: Any) -> Any:
        return self.request("GET", endpoint, params, headers, **request_options).json()

    def get_response(
        self, endpoint: AnyEndpoint, params: Any = None, headers: Any = None, **request_options: Any
    ) -> Response:
        return self.request("GET", endpoint, params, headers, **request_options)

    def get_binary(
        self, endpoint: AnyEndpoint, params: Any = None, headers: Any = None, **request_options: Any
    ) -> bytes:
        return self.request("GET", endpoint, params, headers, **request_options).content

    def post(
        self, endpoint: AnyEndpoint, params: Any = None, headers: Any = None, json: Any = None, **request_options: Any
    ) -> Any:
        return self.request("POST", endpoint, params, headers, json, **request_options).json()

    def put(
        self, endpoint: AnyEndpoint, params: Any = None, headers: Any = None, json: Any = None, **request_options: Any
    ) -> Any:
        return self.request("PUT", endpoint, params, headers, json, **request_options).json()

    def patch(
        self, endpoint: AnyEndpoint, params: Any = None, headers: Any = None, json: Any = None, **request_options: Any
    ) -> Response:
        return self.request("PATCH", endpoint, params, headers, json, **request_options)
