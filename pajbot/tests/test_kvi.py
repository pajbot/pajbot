from typing import List, Optional, Tuple

import pytest


def get_cases() -> List[Tuple[str, Tuple[Optional[str], int]]]:
    return [
        ("key", ("key", 1)),
        ("key 5", ("key", 5)),
        ("key_key 5", ("key_key", 5)),
        ("key 5 ", (None, 1)),
        ("", (None, 1)),
    ]


@pytest.mark.parametrize("input_str,expected", get_cases())
def test_parse_kvi_arguments(input_str: str, expected: Tuple[Optional[str], int]) -> None:
    from pajbot.managers.kvi import parse_kvi_arguments

    assert parse_kvi_arguments(input_str) == expected
