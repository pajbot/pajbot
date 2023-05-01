from __future__ import annotations

from typing import List, Optional

from dataclasses import dataclass

import marshmallow
import marshmallow_dataclass


class BaseSchema(marshmallow.Schema):
    class Meta:
        # Allow for extra fields in the deserialization
        unknown = marshmallow.EXCLUDE


@dataclass
class File:
    name: str
    width: int
    height: int
    format: str


@dataclass
class Host:
    url: str
    files: List[File]


@dataclass
class Data:
    id: str
    name: str
    flags: int
    listed: bool
    animated: bool
    host: Host


@dataclass
class Emote:
    id: str
    name: str
    data: Data


@dataclass
class EmoteSet:
    emotes: Optional[List[Emote]]


@dataclass
class GetTwitchUserResponse:
    emote_set: Optional[EmoteSet]


# From the https://7tv.io/v3/users/twitch/11148817 API
GetTwitchUserResponseSchema = marshmallow_dataclass.class_schema(GetTwitchUserResponse, base_schema=BaseSchema)


@dataclass
class GetEmoteSetResponse:
    emotes: List[Emote]


# From the https://7tv.io/v3/emote-sets/global API
GetEmoteSetResponseSchema = marshmallow_dataclass.class_schema(GetEmoteSetResponse, base_schema=BaseSchema)
