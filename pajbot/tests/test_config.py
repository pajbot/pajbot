from pajbot import config


def test_get_boolean() -> None:
    cfg = {"enabled": "1", "disabled": "0"}

    assert config.get_boolean(cfg, "enabled", False) is True
    assert config.get_boolean(cfg, "disabled", True) is False
    assert config.get_boolean(cfg, "forsen", True) is True
    assert config.get_boolean(cfg, "forsen", False) is False
