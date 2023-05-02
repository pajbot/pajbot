import os

from pajbot.apiwrappers.seventv import SevenTVAPI


def test_seventv_fetch_global_emotes():
    if os.getenv("PAJBOT_RUN_INTEGRATION_TESTS", "0") != "1":
        return

    redis = None
    api = SevenTVAPI(redis)

    emotes = api.fetch_global_emotes()

    assert len(emotes) > 0
