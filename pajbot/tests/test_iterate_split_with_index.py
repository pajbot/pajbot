import pytest

from pajbot.utils import iterate_split_with_index


def test_iterates_correctly():
    # a bcd ef
    generator = iterate_split_with_index(["a", "bcd", "ef"])
    assert next(generator) == (0, "a")
    assert next(generator) == (2, "bcd")
    assert next(generator) == (6, "ef")
    with pytest.raises(StopIteration):
        next(generator)


def test_empty_item():
    # a bcd ef
    generator = iterate_split_with_index(["a", "", "ef"])
    assert next(generator) == (0, "a")
    assert next(generator) == (2, "")
    assert next(generator) == (3, "ef")
    with pytest.raises(StopIteration):
        next(generator)


def test_zero_items():
    generator = iterate_split_with_index([])
    with pytest.raises(StopIteration):
        next(generator)
