def test_find_iterate():
    from pajbot.utils import find

    d = {
        "foo": "1",
        "bar": "2",
        "xD": "3",
    }

    haystack = ["foo", "baz", "bar"]

    print()

    for k, v in d.items():
        needle = find(lambda t: t == k, haystack)
        print(f"{k=} {v=} {needle=}")
