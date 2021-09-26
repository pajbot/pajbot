from typing import Generator, Tuple, List


def iterate_split_with_index(
    split_parts: List[str], separator_length: int = 1
) -> Generator[Tuple[int, str], None, None]:
    """Generator function that for a given list of split parts of a string,
    returns a tuple with the starting index of that split word/part (in the original string) and the part"""
    index = 0
    for part in split_parts:
        yield index, part
        index += len(part) + separator_length
