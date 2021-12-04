from __future__ import annotations

from typing import List

from pajbot.utils import split_into_chunks_with_prefix

import pytest


def test_basic() -> None:
    expected = ["TEST: 1 2 3 4"]
    actual = split_into_chunks_with_prefix([{"prefix": "TEST:", "parts": ["1", "2", "3", "4"]}])
    assert actual == expected


def test_no_parts() -> None:
    expected: List[str] = []
    actual = split_into_chunks_with_prefix([{"prefix": "TEST:", "parts": []}])
    assert actual == expected


def test_default() -> None:
    expected = ["KKona"]
    actual = split_into_chunks_with_prefix([{"prefix": "TEST:", "parts": []}], default="KKona")
    assert actual == expected


def test_multiple_output_messages() -> None:
    expected = ["TEST: ABC DEF GHI JKL MNO PQR", "TEST: STU VWX YZ"]
    actual = split_into_chunks_with_prefix(
        [{"prefix": "TEST:", "parts": ["ABC", "DEF", "GHI", "JKL", "MNO", "PQR", "STU", "VWX", "YZ"]}], limit=30
    )
    assert actual == expected


def test_multiple_chunks_in_same_messages() -> None:
    expected = ["TEST: ABC DEF GHI JKL MNO PQR XD: STU VWX YZ"]
    actual = split_into_chunks_with_prefix(
        [
            {"prefix": "TEST:", "parts": ["ABC", "DEF", "GHI", "JKL", "MNO", "PQR"]},
            {"prefix": "XD:", "parts": ["STU", "VWX", "YZ"]},
        ],
        limit=500,
    )
    assert actual == expected


def test_chunk_boundary_at_message_boundary() -> None:
    expected = ["TEST: ABC DEF GHI JKL MNO PQR", "XD: STU VWX YZ"]
    actual = split_into_chunks_with_prefix(
        [
            {"prefix": "TEST:", "parts": ["ABC", "DEF", "GHI", "JKL", "MNO", "PQR"]},
            {"prefix": "XD:", "parts": ["STU", "VWX", "YZ"]},
        ],
        limit=30,
    )
    assert actual == expected


def test_separator() -> None:
    expected = ["TEST:KKona1KKona2KKona3KKona4"]
    actual = split_into_chunks_with_prefix([{"prefix": "TEST:", "parts": ["1", "2", "3", "4"]}], separator="KKona")
    assert actual == expected


def test_impossible_throws_exception() -> None:
    # not possible to fit this into one message of 30 length
    with pytest.raises(ValueError):
        split_into_chunks_with_prefix([{"prefix": "TEST:", "parts": ["ABCDEFGHIJKLMNOPQRSTUVWXYZ"]}], limit=30)
