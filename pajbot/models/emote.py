from __future__ import annotations

from typing import Any, Dict, List


class Emote:
    """Emote encapsulates an emote that can be from either Twitch, FFZ, BTTV or 7TV.
    :ivar code: Word/code that this emote replaces in the chat message, e.g. "Kappa"
    :type code: str
    :ivar provider: String identifier marking the emote provider. Valid values: "twitch", "ffz", "bttv", "7tv"
    :type provider: str
    :ivar id: Provider-specific ID, e.g. the emote ID for twitch, or the has for bttv.
    :type id: str
    :var urls: Dict mapping size (e.g. "1", "2", or "4") to an URL depicting the emote
    :type urls: dict[str, str]
    :ivar max_width: Width of the largest variant of the emote.
    :type max_width: int
    :ivar max_height: Height of the largest variant of the emote.
    :type max_height: int"""

    def __init__(
        self, code: str, provider: str, id: str, urls: Dict[str, str], max_width: int, max_height: int
    ) -> None:
        self.code = code
        self.provider = provider
        if not isinstance(id, str):
            raise ValueError("id parameter must be a string")
        self.id = id
        self.urls = urls
        self.max_width = max_width
        self.max_height = max_height

    def __eq__(self, other) -> bool:
        if not isinstance(other, Emote):
            return False

        return self.provider == other.provider and self.id == other.id

    def __hash__(self) -> int:
        return hash((self.provider, self.id))

    def __repr__(self) -> str:
        return f"[{self.provider}] {self.code}"

    def jsonify(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "provider": self.provider,
            "id": self.id,
            "urls": self.urls,
            "max_width": self.max_width,
            "max_height": self.max_height,
        }

    @staticmethod
    def from_json(json_data) -> Emote:
        return Emote(**json_data)


class EmoteInstance:
    """A single instance of an emote in a string/message.
    :ivar start: Start index at which the emote occurs (inclusive)
    :type start: int
    :ivar end: End index at which the emote ends (exclusive)
    :type end: int
    :ivar emote: The emote.
    :type emote: Emote"""

    def __init__(self, start: int, end: int, emote: Emote) -> None:
        self.start = start
        self.end = end
        self.emote = emote

    def __eq__(self, other) -> bool:
        if not isinstance(other, EmoteInstance):
            return False

        return self.start == other.start and self.end == other.end and self.emote == other.emote

    def __hash__(self) -> int:
        return hash((self.start, self.end, self.emote))

    def __repr__(self) -> str:
        return f"{self.emote} @ {self.start}-{self.end}"

    def jsonify(self) -> Dict[str, Any]:
        return {"start": self.start, "end": self.end, "emote": self.emote.jsonify()}


class EmoteInstanceCount:
    """An object representing how often an emote occurred in a certain message
    :ivar count: How often `emote` occurred
    :type count: int
    :ivar emote: The emote
    :type emote: Emote
    :ivar emote_instances: List of `EmoteInstance`s that have been grouped together to form this instance
    :type emote_instances: list[EmoteInstance]
    """

    def __init__(self, count: int, emote: Emote, emote_instances: List[EmoteInstance]) -> None:
        self.count = count
        self.emote = emote
        self.emote_instances = emote_instances

    def __eq__(self, other) -> bool:
        if not isinstance(other, EmoteInstanceCount):
            return False

        return self.count == other.count and self.emote == other.emote and self.emote_instances == other.emote_instances

    def __hash__(self) -> int:
        return hash((self.count, self.emote, self.emote_instances))

    def __repr__(self) -> str:
        indices = [f"{instance.start}-{instance.end}" for instance in self.emote_instances]

        return f"{self.emote} @ [{', '.join(indices)}]"

    def jsonify(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "emote": self.emote.jsonify(),
            "emote_instances": [i.jsonify() for i in self.emote_instances],
        }


EmoteInstanceCountMap = Dict[str, EmoteInstanceCount]
