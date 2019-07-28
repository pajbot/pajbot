import pytest

from pajbot.utils import split_into_chunks_with_prefix


def test_basic():
    expected = ["TEST: 1 2 3 4"]
    actual = split_into_chunks_with_prefix([{"prefix": "TEST:", "parts": ["1", "2", "3", "4"]}])
    assert actual == expected


def test_no_parts():
    expected = []
    actual = split_into_chunks_with_prefix([{"prefix": "TEST:", "parts": []}])
    assert actual == expected


def test_default():
    expected = ["KKona"]
    actual = split_into_chunks_with_prefix([{"prefix": "TEST:", "parts": []}], default="KKona")
    assert actual == expected


def test_multiple_output_messages():
    expected = ["TEST: ABC DEF GHI JKL MNO PQR", "TEST: STU VWX YZ"]
    actual = split_into_chunks_with_prefix(
        [{"prefix": "TEST:", "parts": ["ABC", "DEF", "GHI", "JKL", "MNO", "PQR", "STU", "VWX", "YZ"]}], limit=30
    )
    assert actual == expected


def test_multiple_chunks_in_same_messages():
    expected = ["TEST: ABC DEF GHI JKL MNO PQR XD: STU VWX YZ"]
    actual = split_into_chunks_with_prefix(
        [
            {"prefix": "TEST:", "parts": ["ABC", "DEF", "GHI", "JKL", "MNO", "PQR"]},
            {"prefix": "XD:", "parts": ["STU", "VWX", "YZ"]},
        ],
        limit=500,
    )
    assert actual == expected


def test_chunk_boundary_at_message_boundary():
    expected = ["TEST: ABC DEF GHI JKL MNO PQR", "XD: STU VWX YZ"]
    actual = split_into_chunks_with_prefix(
        [
            {"prefix": "TEST:", "parts": ["ABC", "DEF", "GHI", "JKL", "MNO", "PQR"]},
            {"prefix": "XD:", "parts": ["STU", "VWX", "YZ"]},
        ],
        limit=30,
    )
    assert actual == expected


def test_separator():
    expected = ["TEST:KKona1KKona2KKona3KKona4"]
    actual = split_into_chunks_with_prefix([{"prefix": "TEST:", "parts": ["1", "2", "3", "4"]}], separator="KKona")
    assert actual == expected


def test_impossible_throws_exception():
    # not possible to fit this into one message of 30 length
    with pytest.raises(ValueError):
        split_into_chunks_with_prefix([{"prefix": "TEST:", "parts": ["ABCDEFGHIJKLMNOPQRSTUVWXYZ"]}], limit=30)
