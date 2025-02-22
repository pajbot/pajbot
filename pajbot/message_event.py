from dataclasses import dataclass
from typing import Literal


@dataclass
class MessageEvent:
    type: Literal["action", "message"]

    """
    Target of the message (e.g. #forsen for a normal message or forsen for a whisper to forsen)
    """
    target: str

    num_bits_spent: int
