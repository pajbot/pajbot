import datetime
from abc import ABC, abstractmethod

import pajbot


class AccessToken(ABC):

    SHOULD_REFRESH_THRESHOLD = 0.9
    """Fraction between 0 and 1 indicating what fraction/percentage of the specified full validity period
    should actually be utilized. E.g. if this is set to 0.9, the implementation will refresh the token
    once at least 90% of the full validity period (expires_in) is over."""

    def __init__(self, access_token, created_at, expires_in, token_type, refresh_token, scope):
        self.access_token = access_token

        self.created_at = created_at

        # can both be None
        self.expires_in = expires_in
        if self.expires_in is not None:
            self.expires_at = self.created_at + self.expires_in
        else:
            self.expires_at = None

        self.token_type = token_type

        # can be None
        self.refresh_token = refresh_token

        # always a list, can be empty list
        self.scope = scope

    @abstractmethod
    def can_refresh(self):
        pass

    def should_refresh(self):
        """Returns True if less than 10% of the token's lifetime remains, False otherwise"""

        if not self.can_refresh():
            return False

        # intended lifetime of the token
        if self.expires_at is not None:
            expires_after = self.expires_at - self.created_at
        else:
            # this is a token that never expires
            # because we don't want any issues, refresh it anyways
            expires_after = datetime.timedelta(hours=1)

        # how much time has passed since token creation
        token_age = pajbot.utils.now() - self.created_at

        # maximum token age before token should be refreshed (90% of the total token lifetime)
        max_token_age = expires_after * self.SHOULD_REFRESH_THRESHOLD

        # expired?
        return token_age >= max_token_age

    def jsonify(self):
        """serialize for storage"""
        if self.expires_in is None:
            expires_in_milliseconds = None
        else:
            expires_in_milliseconds = self.expires_in.total_seconds() * 1000

        return {
            "access_token": self.access_token,
            "created_at": self.created_at.timestamp() * 1000,
            "expires_in": expires_in_milliseconds,
            "token_type": self.token_type,
            "refresh_token": self.refresh_token,
            "scope": self.scope,
        }

    @classmethod
    def from_json(cls, json_data):
        """deserialize json produced by jsonify()"""
        if json_data["expires_in"] is None:
            expires_in = None
        else:
            expires_in = datetime.timedelta(milliseconds=json_data["expires_in"])

        return cls(
            access_token=json_data["access_token"],
            created_at=pajbot.utils.datetime_from_utc_milliseconds(json_data["created_at"]),
            expires_in=expires_in,
            token_type=json_data["token_type"],
            refresh_token=json_data["refresh_token"],
            scope=json_data["scope"],
        )

    @classmethod
    def from_api_response(cls, response):
        """Construct new object from twitch response json data"""

        # expires_in is only missing for old Client-IDs to which twitch will respond with
        # infinitely-lived tokens (the "expires_in" field is absent in that case).
        expires_in_seconds = response.get("expires_in", None)
        if expires_in_seconds is None:
            expires_in = None
        else:
            expires_in = datetime.timedelta(seconds=expires_in_seconds)

        return cls(
            access_token=response["access_token"],
            created_at=pajbot.utils.now(),
            expires_in=expires_in,
            token_type=response["token_type"],
            refresh_token=response.get("refresh_token", None),
            scope=response.get("scope", []),
        )

    @abstractmethod
    def refresh(self, api):
        pass


class UserAccessToken(AccessToken):
    def can_refresh(self):
        return self.refresh_token is not None

    def refresh(self, api):
        if not self.can_refresh():
            raise ValueError("This user access token cannot be refreshed, it has no refresh token")

        return api.refresh_user_access_token(self.refresh_token)

    @staticmethod
    def from_implicit_auth_flow_token(access_token):
        return UserAccessToken(
            access_token=access_token,
            created_at=None,
            expires_in=None,
            token_type="bearer",
            refresh_token=None,
            scope=[],
        )


class AppAccessToken(AccessToken):
    def can_refresh(self):
        return True

    def refresh(self, api):
        return api.get_app_access_token(self.scope)
