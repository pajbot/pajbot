import os

from pajbot.apiwrappers.seventv import SevenTVAPI


def test_seventv_fetch_channel_emotes_has_emotes():
    """
    The user pajlada (User ID 11148817) have signed up to 7TV and
    have added emotes.
    """

    if os.getenv("PAJBOT_RUN_INTEGRATION_TESTS", "0") != "1":
        return

    redis = None
    api = SevenTVAPI(redis)

    emotes = api.fetch_channel_emotes("11148817")

    assert len(emotes) > 0


def test_seventv_fetch_channel_emotes_unknown_user():
    """
    The user testaccount_420 (User ID 117166826) have not signed up to 7TV.
    """

    if os.getenv("PAJBOT_RUN_INTEGRATION_TESTS", "0") != "1":
        return

    redis = None
    api = SevenTVAPI(redis)

    emotes = api.fetch_channel_emotes("117166826")

    assert len(emotes) == 0


def test_seventv_fetch_channel_emotes_no_emote_set():
    """
    The user bajlada (User ID 159849156) is signed up to 7TV but have
    not created an emote set
    """

    if os.getenv("PAJBOT_RUN_INTEGRATION_TESTS", "0") != "1":
        return

    redis = None
    api = SevenTVAPI(redis)

    emotes = api.fetch_channel_emotes("159849156")

    assert len(emotes) == 0


def test_seventv_fetch_channel_emotes_emote_set_but_no_emotes():
    """
    The user pajbot (User ID 82008718) is signed up to 7TV.
    They have created an emote set, but have not added any emotes
    """

    if os.getenv("PAJBOT_RUN_INTEGRATION_TESTS", "0") != "1":
        return

    redis = None
    api = SevenTVAPI(redis)

    emotes = api.fetch_channel_emotes("82008718")

    assert len(emotes) == 0
