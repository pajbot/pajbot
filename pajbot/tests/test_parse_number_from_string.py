import pytest

from pajbot.utils import parse_number_from_string


def test_valid_int_conversions() -> None:
    # key = input
    # value = expected value
    tests = {
        "1": 1,
        "2": 2,
        "3": 3,
        "503": 503,
        "-503": -503,
        "503 ": 503,  # Spaces are valid in int() and float()
        "           503 ": 503,  # Spaces are valid in int() and float()
    }

    for input_value in tests:
        expected_value = tests[input_value]
        output_value = parse_number_from_string(input_value)

        assert type(output_value) == type(expected_value)
        assert output_value == expected_value


def test_valid_float_conversions() -> None:
    # key = input
    # value = expected value
    tests = {
        "1.0": 1.0,
        "2.5": 2.5,
        "503.0": 503.0,
        "1.111": 1.111,
        "-503.5": -503.5,
        "503.5 ": 503.5,  # Spaces are valid in int() and float()
        "           503.7 ": 503.7,  # Spaces are valid in int() and float()
    }

    for input_value in tests:
        expected_value = tests[input_value]
        output_value = parse_number_from_string(input_value)

        assert type(output_value) == type(expected_value)
        assert output_value == expected_value


def test_bad_conversions_full_string() -> None:
    input_value = "xd"

    with pytest.raises(ValueError):
        parse_number_from_string(input_value)


def test_bad_conversions_string_suffix() -> None:
    input_value = "1a"

    with pytest.raises(ValueError):
        parse_number_from_string(input_value)


def test_bad_conversions_string_prefix() -> None:
    input_value = "a1"

    with pytest.raises(ValueError):
        parse_number_from_string(input_value)


def test_bad_conversions_string_suffix_float() -> None:
    input_value = "503.0a"

    with pytest.raises(ValueError):
        parse_number_from_string(input_value)


def test_bad_conversions_string_prefix_float() -> None:
    input_value = "a1.111"

    with pytest.raises(ValueError):
        parse_number_from_string(input_value)


def test_bad_conversions_empty() -> None:
    input_value = ""

    with pytest.raises(ValueError):
        parse_number_from_string(input_value)


def test_bad_conversions_space() -> None:
    input_value = " "

    with pytest.raises(ValueError):
        parse_number_from_string(input_value)
