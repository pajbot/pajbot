from typing import Iterable, TypeVar

T = TypeVar("T")


def iterate_in_chunks(seq: list[T], chunk_size: int) -> Iterable[list[T]]:
    return (seq[pos : pos + chunk_size] for pos in range(0, len(seq), chunk_size))
