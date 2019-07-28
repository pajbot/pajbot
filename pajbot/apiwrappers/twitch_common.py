import datetime

from abc import ABC, abstractmethod

from pajbot.apiwrappers.apiwrappers import BaseApi


class BaseTwitchApi(BaseApi, ABC):
    def __init__(self, base_url, client_id=None, oauth=None, default_headers=None):
        if default_headers is None:
            default_headers = {}

        if client_id:
            default_headers["Client-ID"] = client_id
        if oauth:
            default_headers["Authorization"] = self.authorization_header_prefix + " " + oauth

        if client_id is None and oauth is None:
            raise ValueError("At least one of client_id or oauth must be specified")

        super().__init__(base_url, default_headers)

    @staticmethod
    def parse_datetime(datetime_str):
        """Parses date strings in the format of 2015-09-11T23:01:11Z
        to a tz-aware datetime object."""
        naive_dt = datetime.datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%SZ")
        return naive_dt.replace(tzinfo=datetime.timezone.utc)

    @property
    @abstractmethod
    def authorization_header_prefix(self):
        """ "OAuth" for kraken, "Bearer" for the new helix api"""
        pass


class BaseTwitchKrakenAPI(BaseTwitchApi):
    authorization_header_prefix = "OAuth"
