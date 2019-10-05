class Emote:
    """Emote encapsulates an emote that can be from either Twitch, FFZ or BTTV.
    :ivar code: Word/code that this emote replaces in the chat message, e.g. "Kappa"
    :type code: str
    :ivar provider: String identifier marking the emote provider. Valid values: "twitch", "ffz", "bttv"
    :type provider: str
    :ivar id: Provider-specific ID, e.g. the emote ID for twitch, or the has for bttv.
    :type id: str
    :var urls: Dict mapping size (e.g. "1", "2", or "4") to an URL depicting the emote
    :type urls: dict[str, str]"""

    def __init__(self, code, provider, id, urls):
        self.code = code
        self.provider = provider
        self.id = id
        self.urls = urls

    def __eq__(self, other):
        if not isinstance(other, Emote):
            return False

        return self.provider == other.provider and self.id == other.id

    def __hash__(self):
        return hash((self.provider, self.id))

    def __repr__(self):
        return f"[{self.provider}] {self.code}"

    def jsonify(self):
        return {"code": self.code, "provider": self.provider, "id": self.id, "urls": self.urls}

    @staticmethod
    def from_json(json_data):
        return Emote(**json_data)


class EmoteInstance:
    """A single instance of an emote in a string/message.
    :ivar start: Start index at which the emote occurs (inclusive)
    :type start: int
    :ivar end: End index at which the emote ends (exclusive)
    :type end: int
    :ivar emote: The emote.
    :type emote: Emote"""

    def __init__(self, start, end, emote):
        self.start = start
        self.end = end
        self.emote = emote

    def __eq__(self, other):
        if not isinstance(other, EmoteInstance):
            return False

        return self.start == other.start and self.end == other.end and self.emote == other.emote

    def __hash__(self):
        return hash((self.start, self.end, self.emote))

    def __repr__(self):
        return f"{self.emote} @ {self.start}-{self.end}"

    def jsonify(self):
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

    def __init__(self, count, emote, emote_instances):
        self.count = count
        self.emote = emote
        self.emote_instances = emote_instances

    def __eq__(self, other):
        if not isinstance(other, EmoteInstanceCount):
            return False

        return self.count == other.count and self.emote == other.emote and self.emote_instances == other.emote_instances

    def __hash__(self):
        return hash((self.count, self.emote, self.emote_instances))

    def __repr__(self):
        indices = [f"{instance.start}-{instance.end}" for instance in self.emote_instances]

        return f"{self.emote} @ [{', '.join(indices)}]"

    def jsonify(self):
        return {
            "count": self.count,
            "emote": self.emote.jsonify(),
            "emote_instances": [i.jsonify() for i in self.emote_instances],
        }
