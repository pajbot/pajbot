from typing import Dict, List, Optional, Tuple

from pajbot.models.action import Substitution

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


def get_argument_substitutions_cases() -> List[Tuple[str, List[Substitution]]]:
    return [
        ("foo", []),
        ("foo $(1) bar", [Substitution(None, needle="$(1)", argument=1)]),
    ]


@pytest.mark.parametrize("input_message,expected_substitutions", get_argument_substitutions_cases())
def test_argument_substitutions(input_message: str, expected_substitutions: List[Substitution]):
    from pajbot.models.action import get_argument_substitutions

    assert get_argument_substitutions(input_message) == expected_substitutions


method_mapping = {"foo": lambda x: "bar"}


def get_substitutions_cases() -> List[Tuple[str, Dict[str, Substitution]]]:
    return [
        ("foo", {}),
        ("foo $(1) bar", {}),
        ("foo $(foo) bar", {"$(foo)": Substitution(method_mapping["foo"], needle="$(foo)", key=None, argument=None)}),
        (
            "foo $(foo:bar) bar",
            {"$(foo:bar)": Substitution(method_mapping["foo"], needle="$(foo:bar)", key="bar", argument=None)},
        ),
        (
            'foo $(foo:"bar", "baz") bar',
            {
                '$(foo:"bar", "baz")': Substitution(
                    method_mapping["foo"], needle='$(foo:"bar", "baz")', key='"bar", "baz"', argument=None
                )
            },
        ),
        (
            'foo $(foo:"bingo bango", "baz") bar',
            {
                '$(foo:"bingo bango", "baz")': Substitution(
                    method_mapping["foo"],
                    needle='$(foo:"bingo bango", "baz")',
                    key='"bingo bango", "baz"',
                    argument=None,
                )
            },
        ),
    ]


@pytest.mark.parametrize("input_message,expected_substitutions", get_substitutions_cases())
def test_substitutions(input_message: str, expected_substitutions: Dict[str, Substitution]):
    from pajbot.models.action import get_substitutions

    assert get_substitutions(input_message, None, method_mapping=method_mapping) == expected_substitutions
