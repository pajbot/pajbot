from pajbot.modules.bingo import two_word_variations


def test_two_word_variations():
    assert two_word_variations("abc", "def", "KKona") == {
        "abc-def": "KKona",
        "abc_def": "KKona",
        "abcdef": "KKona",
        "def-abc": "KKona",
        "def_abc": "KKona",
        "defabc": "KKona",
    }
