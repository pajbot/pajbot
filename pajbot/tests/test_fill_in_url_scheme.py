from pajbot.apiwrappers.common import fill_in_url_scheme


def test_fills_in_relative_url():
    assert fill_in_url_scheme("//example.com") == "https://example.com"


def test_respects_passed_scheme():
    assert fill_in_url_scheme("//example.com", "wss") == "wss://example.com"


def test_does_not_change_non_relative_urls():
    assert fill_in_url_scheme("http://example.com") == "http://example.com"
