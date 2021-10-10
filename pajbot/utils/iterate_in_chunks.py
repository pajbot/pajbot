from typing import Iterable, List, TypeVar

T = TypeVar("T")


def iterate_in_chunks(seq: List[T], chunk_size: int) -> Iterable[List[T]]:
    return (seq[pos : pos + chunk_size] for pos in range(0, len(seq), chunk_size))
