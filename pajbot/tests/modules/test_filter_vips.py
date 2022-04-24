from typing import List, Tuple

from pajbot.modules.vip_refresh import VIPRefreshModule

import pytest


def get_filter_vips_cases() -> List[Tuple[List[str], List[str]]]:
    return [
        # Standard login names
        (["foo"], ["foo"]),
        (["Pajlada"], ["Pajlada"]),
        (["pajlada", "forsen"], ["pajlada", "forsen"]),
        # Display names where they're ascii-only but contain uppercase characters
        (["pajlada", "FORSEN"], ["pajlada", "FORSEN"]),
        # Display names with spaces in the middle should be filtered out
        (["pajlada", "Riot Games", "forsen"], ["pajlada", "forsen"]),
        # Display names with spaces at the end should be filtered out
        (["pajlada", "testman ", "forsen"], ["pajlada", "forsen"]),
        # Display names with spaces at the start should be filtered out
        (["pajlada", " testman", "forsen"], ["pajlada", "forsen"]),
        # Display names non-ascii characters should be filtered out
        (["pajlada", "테스트계정420", "forsen"], ["pajlada", "forsen"]),
        # Names cannot start with _
        # Names can contain _ just not at the start
        (["_pajlada"], []),
        (["pajlada_"], ["pajlada_"]),
        # Empty list
        ([], []),
    ]


@pytest.mark.parametrize("input_vips,expected_vips", get_filter_vips_cases())
def test_filter_vips(input_vips: List[str], expected_vips: List[str]) -> None:
    assert VIPRefreshModule._filter_vips(input_vips) == expected_vips
