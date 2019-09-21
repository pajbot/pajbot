def test_is_subdomain():
    from pajbot.modules.linkchecker import is_subdomain

    assert is_subdomain("pajlada.se", "pajlada.se")
    assert is_subdomain("test.pajlada.se", "pajlada.se")

    assert not is_subdomain("test.pajlada.se", "pajlada.com")
    assert not is_subdomain("kastaren.com", "roleplayer.se")
    assert not is_subdomain("foo.bar.com", "foobar.com")


def test_is_subpath():
    from pajbot.modules.linkchecker import is_subpath

    assert is_subpath("/foo/", "/foo/")
    assert is_subpath("/foo/bar", "/foo/")

    assert not is_subpath("/foo/", "/bar/")
    assert not is_subpath("/foo/", "/foo/bar")


def test_is_same_url():
    from pajbot.modules.linkchecker import is_same_url, Url

    assert is_same_url(Url("pajlada.se"), Url("pajlada.se/"))

    assert not is_same_url(Url("pajlada.com"), Url("pajlada.se"))
    assert not is_same_url(Url("pajlada.com"), Url("pajlada.com/abc"))


def test_find_unique_urls():
    from pajbot.modules.linkchecker import find_unique_urls
    from pajbot.bot import URL_REGEX

    assert find_unique_urls(URL_REGEX, "pajlada.se test http://pajlada.se") == {"http://pajlada.se"}
    assert find_unique_urls(URL_REGEX, "pajlada.se pajlada.com foobar.se") == {
        "http://pajlada.se",
        "http://pajlada.com",
        "http://foobar.se",
    }
    assert find_unique_urls(URL_REGEX, "foobar.com foobar.com") == {"http://foobar.com"}
    assert find_unique_urls(URL_REGEX, "foobar.com foobar.se"), {"http://foobar.com" == "http://foobar.se"}
    assert find_unique_urls(URL_REGEX, "www.foobar.com foobar.se"), {"http://www.foobar.com" == "http://foobar.se"}

    # TODO: Edge case, this behaviour should probably be changed. These URLs should be considered the same.
    # Use is_same_url method?
    assert find_unique_urls(URL_REGEX, "pajlada.se/ pajlada.se"), {"http://pajlada.se/" == "http://pajlada.se"}

    # TODO: The protocol of a URL is entirely thrown away, this behaviour should probably be changed.
    assert find_unique_urls(URL_REGEX, "https://pajlada.se/ https://pajlada.se") == {
        "https://pajlada.se/",
        "https://pajlada.se",
    }
