from typing import List, Optional, Tuple

import pytest


def get_argument_value_cases() -> List[Tuple[Optional[str], Optional[int], str]]:
    return [
        ("foo bar", 1, "foo"),
        ("foo bar", 0, ""),
        ("foo bar", None, ""),
        (None, None, ""),
        (None, 1, ""),
        ("foo bar", 2, "bar"),
        ("foo bar", 3, ""),
        ("foo", 2, ""),
        ("foo", 1, "foo"),
    ]


@pytest.mark.parametrize("input_message,input_index,expected", get_argument_value_cases())
def test_get_argument_value(input_message: Optional[str], input_index: Optional[int], expected: str) -> None:
    from pajbot.models.action import get_argument_value

    assert get_argument_value(input_message, input_index) == expected
