from typing import Iterator


def iterate_split_with_index(split_parts: list[str], separator_length: int = 1) -> Iterator[tuple[int, str]]:
    """Generator function that for a given list of split parts of a string,
    returns a tuple with the starting index of that split word/part (in the original string) and the part"""
    index = 0
    for part in split_parts:
        yield index, part
        index += len(part) + separator_length
