from typing import Callable, Iterable, Optional, TypeVar

T = TypeVar("T")


def find(predicate: Callable[[T], bool], seq: Iterable[T]) -> Optional[T]:
    """Method shamelessly taken from https://github.com/Rapptz/discord.py"""

    for element in seq:
        if predicate(element):
            return element
    return None
