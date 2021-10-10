def test_find_iterate():
    from pajbot.utils import find

    d = {
        "foo": True,
        "bar": True,
        "xD": False,
    }

    haystack = ["foo", "baz", "bar"]

    for k, v in d.items():
        needle = find(lambda t: t == k, haystack)
        if v:
            assert needle == k
        else:
            assert needle is None
