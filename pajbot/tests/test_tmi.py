import pytest

from pajbot.tmi import ChatOutputMode


def test_chat_output_mode_parses_valid_values() -> None:
    assert ChatOutputMode.from_config_value("helix") == ChatOutputMode.HELIX
    assert ChatOutputMode.from_config_value("HELIX") == ChatOutputMode.HELIX
    assert ChatOutputMode.from_config_value("irc") == ChatOutputMode.IRC
    assert ChatOutputMode.from_config_value("IRC") == ChatOutputMode.IRC


def test_chat_output_mode_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="chat_output_mode"):
        ChatOutputMode.from_config_value("legacy")
