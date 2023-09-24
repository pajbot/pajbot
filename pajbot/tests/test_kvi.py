from typing import Optional

import pytest


def get_cases() -> list[tuple[str, tuple[Optional[str], int]]]:
    return [
        ("key", ("key", 1)),
        ("key 5", ("key", 5)),
        ("key_key 5", ("key_key", 5)),
        ("key 5 ", (None, 1)),
        ("", (None, 1)),
    ]


@pytest.mark.parametrize("input_str,expected", get_cases())
def test_parse_kvi_arguments(input_str: str, expected: tuple[Optional[str], int]) -> None:
    from pajbot.managers.kvi import parse_kvi_arguments

    assert parse_kvi_arguments(input_str) == expected
