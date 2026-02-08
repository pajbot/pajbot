import pytest

from pajbot.apiwrappers.twitch.helix import TwitchHelixAPI


def test_send_chat_message_posts_expected_payload() -> None:
    api = TwitchHelixAPI(redis=None, app_token_manager=None)

    captured = {}

    def fake_post(endpoint, params=None, headers=None, authorization=None, json=None):
        captured["endpoint"] = endpoint
        captured["params"] = params
        captured["headers"] = headers
        captured["authorization"] = authorization
        captured["json"] = json
        return {"data": [{"is_sent": True}]}

    api.post = fake_post

    api.send_chat_message(
        broadcaster_id="123",
        sender_id="456",
        message="hello world",
        authorization="authz",
        reply_parent_message_id="789",
    )

    assert captured["endpoint"] == "/chat/messages"
    assert captured["params"] is None
    assert captured["authorization"] == "authz"
    assert captured["json"] == {
        "broadcaster_id": "123",
        "sender_id": "456",
        "message": "hello world",
        "reply_parent_message_id": "789",
    }


def test_send_chat_message_raises_when_message_is_rejected() -> None:
    api = TwitchHelixAPI(redis=None, app_token_manager=None)

    api.post = lambda *args, **kwargs: {
        "data": [
            {
                "is_sent": False,
                "drop_reason": {"code": "automod_held", "message": "This message requires review"},
            }
        ]
    }

    with pytest.raises(ValueError, match="automod_held"):
        api.send_chat_message(
            broadcaster_id="123",
            sender_id="456",
            message="hello world",
            authorization="authz",
        )


def test_send_chat_message_raises_on_empty_response_data() -> None:
    api = TwitchHelixAPI(redis=None, app_token_manager=None)

    api.post = lambda *args, **kwargs: {"data": []}

    with pytest.raises(ValueError, match="did not contain any message status"):
        api.send_chat_message(
            broadcaster_id="123",
            sender_id="456",
            message="hello world",
            authorization="authz",
        )
