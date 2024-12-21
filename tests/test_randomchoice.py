import pytest


def randomchoice_cases() -> list[tuple[str, list[str]]]:
    return [
        ('"foo"', ["foo"]),
        ('"foo""bar"', ["foo", "bar"]),
        ('"foo" "bar"', ["foo", "bar"]),
        ('"foo","bar"', ["foo", "bar"]),
        ('"foo","bar"', ["foo", "bar"]),
        ('"foo"    "bar"', ["foo", "bar"]),
        ('""', [""]),
        ('"foo.bar"', ["foo.bar"]),
        ('"foo,bar"', ["foo,bar"]),
        (
            '"foo:bar"',
            [],
        ),  # : is not allowed because it wouldn't pass the model action regex
        ('"foo bar"', ["foo bar"]),
        ('"foo bar", "foo"', ["foo bar", "foo"]),
    ]


@pytest.mark.parametrize("input_string,expected_matches", randomchoice_cases())
def test_get_argument_value(input_string: str, expected_matches: list[str]) -> None:
    from pajbot.bot import RANDOMCHOICE_ARGUMENT_REGEX

    matches = RANDOMCHOICE_ARGUMENT_REGEX.findall(input_string)

    assert matches == expected_matches
