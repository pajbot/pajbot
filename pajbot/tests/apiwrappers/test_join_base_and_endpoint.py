from pajbot.apiwrappers.base import BaseApi


def test_string_endpoint_no_leading_slash():
    assert BaseApi.join_base_and_endpoint("https://example.com/v1/", "test/def") == "https://example.com/v1/test/def"
    assert BaseApi.join_base_and_endpoint("https://example.com/v1/", "/test/def") == "https://example.com/v1/test/def"
    assert BaseApi.join_base_and_endpoint("https://example.com/v1", "test/def") == "https://example.com/v1/test/def"
    assert BaseApi.join_base_and_endpoint("https://example.com/v1", "/test/def") == "https://example.com/v1/test/def"


def test_list_endpoint():
    assert (
        BaseApi.join_base_and_endpoint("https://example.com/v1/", ["test", "def"]) == "https://example.com/v1/test/def"
    )
    assert (
        BaseApi.join_base_and_endpoint("https://example.com/v1", ["test", "def"]) == "https://example.com/v1/test/def"
    )


def test_list_endpoint_with_int_path_segment():
    assert (
        BaseApi.join_base_and_endpoint("https://example.com/v1", ["test", 1234]) == "https://example.com/v1/test/1234"
    )


def test_safebrowsing():
    assert (
        BaseApi.join_base_and_endpoint("https://safebrowsing.googleapis.com/v4/", "/threatMatches:find")
        == "https://safebrowsing.googleapis.com/v4/threatMatches:find"
    )


def test_list_endpoint_escaping():
    assert (
        BaseApi.join_base_and_endpoint("https://example.com/v1/", ["test", "/some Data/"])
        == "https://example.com/v1/test/%2Fsome%20Data%2F"
    )
