from pajbot.utils.now import now


def test_now() -> None:
    b = now()  # i just want to make sure deprecation checking works
    assert b.tzname() == "UTC"
