from pajbot.modules.bingo import join_to_sentence


def test_length_zero():
    assert join_to_sentence([]) == ""


def test_length_one():
    assert join_to_sentence(["asd"]) == "asd"


def test_length_two():
    assert join_to_sentence(["asd", "def"]) == "asd and def"


def test_length_three():
    assert join_to_sentence(["asd", "def", "KKona"]) == "asd, def and KKona"


def test_length_four():
    assert join_to_sentence(["asd", "def", "KKona", "xD"]) == "asd, def, KKona and xD"


def test_custom_separators():
    assert join_to_sentence(["asd", "def", "KKona", "xD"], ";", " et ") == "asd;def;KKona et xD"
