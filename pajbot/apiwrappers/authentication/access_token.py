from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from typing import Any, Protocol, Type, TypeVar

import pajbot
from pajbot.apiwrappers.authentication.client_credentials import ClientCredentials
import pajbot.utils

_T = TypeVar("_T", bound="AccessToken")


class IdentityAPI(Protocol):
    def get_client_credentials(self) -> ClientCredentials: ...

    async def get_app_access_token(self, scope: list[str]) -> AppAccessToken: ...

    async def refresh_user_access_token(self, refresh_token: str) -> UserAccessToken: ...


class AccessToken(ABC):
    SHOULD_REFRESH_THRESHOLD = 0.9
    """Fraction between 0 and 1 indicating what fraction/percentage of the specified full validity period
    should actually be utilized. E.g. if this is set to 0.9, the implementation will refresh the token
    once at least 90% of the full validity period (expires_in) is over."""

    def __init__(
        self,
        access_token: str,
        created_at: datetime.datetime | None,
        expires_in: datetime.timedelta | None,
        token_type: str,
        refresh_token: str | None,
        scope: list[str],
    ) -> None:
        self.access_token = access_token

        self.created_at = created_at

        # can both be None
        self.expires_in = expires_in
        self.expires_at: datetime.datetime | None = None
        if self.expires_in is not None and self.created_at is not None:
            self.expires_at = self.created_at + self.expires_in

        self.token_type = token_type

        # can be None
        self.refresh_token = refresh_token

        # always a list, can be empty list
        self.scope = scope

    @abstractmethod
    def can_refresh(self) -> bool: ...

    def should_refresh(self) -> bool:
        """Returns True if less than 10% of the token's lifetime remains, False otherwise"""

        if not self.can_refresh():
            return False

        # intended lifetime of the token
        if self.expires_at is not None and self.created_at is not None:
            expires_after = self.expires_at - self.created_at
            # how much time has passed since token creation
            token_age = pajbot.utils.now() - self.created_at
        else:
            # this is a token that never expires
            # because we don't want any issues, refresh it anyways
            expires_after = datetime.timedelta(hours=1)
            token_age = datetime.timedelta(hours=0)

        # maximum token age before token should be refreshed (90% of the total token lifetime)
        max_token_age = expires_after * self.SHOULD_REFRESH_THRESHOLD

        # expired?
        return token_age >= max_token_age

    def jsonify(self) -> dict[str, Any]:
        """serialize for storage"""
        if self.expires_in is None:
            expires_in_milliseconds = None
        else:
            expires_in_milliseconds = self.expires_in.total_seconds() * 1000

        return {
            "access_token": self.access_token,
            "created_at": (self.created_at.timestamp()) if self.created_at is not None else 0 * 1000,
            "expires_in": expires_in_milliseconds,
            "token_type": self.token_type,
            "refresh_token": self.refresh_token,
            "scope": self.scope,
        }

    @classmethod
    def from_json(cls: Type[_T], json_data: dict[str, Any]) -> _T:
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
    def from_api_response(cls: Type[_T], response: dict[str, Any]) -> _T:
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
    async def refresh(self, api: IdentityAPI) -> AccessToken:
        pass


class UserAccessToken(AccessToken):
    def can_refresh(self) -> bool:
        return self.refresh_token is not None

    async def refresh(self, api: IdentityAPI) -> UserAccessToken:
        if not self.can_refresh():
            raise ValueError("This user access token cannot be refreshed, it has no refresh token")

        if self.refresh_token is None:
            raise ValueError("This user access token cannot be refreshed, it has no refresh token")

        return await api.refresh_user_access_token(self.refresh_token)

    @staticmethod
    def from_implicit_auth_flow_token(access_token: str) -> UserAccessToken:
        return UserAccessToken(
            access_token=access_token,
            created_at=None,
            expires_in=None,
            token_type="bearer",
            refresh_token=None,
            scope=[],
        )


class AppAccessToken(AccessToken):
    def can_refresh(self) -> bool:
        return True

    async def refresh(self, api: IdentityAPI) -> AppAccessToken:
        return await api.get_app_access_token(self.scope)
