from pajbot.modules.bingo import remove_emotes_suffix


def test_remove_emotes_suffix():
    assert remove_emotes_suffix("kkona") == "kkona"
    assert remove_emotes_suffix("kkona-emotes") == "kkona"
    assert remove_emotes_suffix("kkona-emote") == "kkona"
    assert remove_emotes_suffix("kkona_emotes") == "kkona"
    assert remove_emotes_suffix("kkona_emote") == "kkona"
    assert remove_emotes_suffix("kkonaemotes") == "kkona"
    assert remove_emotes_suffix("kkonaemote") == "kkona"
    assert remove_emotes_suffix("kkona-EMOTES") == "kkona"
    assert remove_emotes_suffix("KKona-emotes") == "KKona"
    assert remove_emotes_suffix("KKona-somethingelse") == "KKona-somethingelse"
    assert remove_emotes_suffix("") == ""
