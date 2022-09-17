from typing import List, Tuple

from pajbot.modules.trivia import TriviaModule

import pytest


def get_valid_cases() -> List[Tuple[Tuple[str, str], bool]]:
    # (user_answer, correct_answer)
    return [
        (("foo", "foo"), True),
        (("fooba", "fooab"), False),
        # Incorrect but close enough
        (("the eifel tower", "the eiffel tower"), True),
        # Too incorrect
        (("the eifel towerr", "the eiffel tower"), False),
    ]


@pytest.mark.parametrize("input,expected", get_valid_cases())
def test_trivia_confirm_answer(input: Tuple[str, str], expected: bool) -> None:
    user_answer = input[0]
    correct_answer = input[1]
    assert TriviaModule.confirm_answer(user_answer, correct_answer) == expected


def get_error_cases() -> List[Tuple[Tuple[str, str], bool]]:
    # (user_answer, correct_answer)
    return [
        (("Foo", "foo"), True),
        (("foo", "Foo"), True),
    ]


@pytest.mark.parametrize("input,expected", get_error_cases())
def test_trivia_confirm_answer_errors(input: Tuple[str, str], expected: bool) -> None:
    user_answer = input[0]
    correct_answer = input[1]

    with pytest.raises(AssertionError):
        assert TriviaModule.confirm_answer(user_answer, correct_answer) == expected
