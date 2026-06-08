import datetime
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock

from pajbot.modules.longtimeout import (
    TWITCH_MAX_TIMEOUT_SECONDS,
    LongTimeoutModule,
    apply_long_timeout,
    format_timeout_end,
    get_long_timeout_duration_seconds,
    long_timeout_reason,
    parse_long_timeout_end,
    parse_twitch_timeout_end,
    should_refresh_long_timeout,
)

import pytest
from requests import HTTPError, Response


def test_parse_long_timeout_end_duration():
    now = datetime.datetime(2026, 6, 2, 10, 0, 0, tzinfo=datetime.timezone.utc)

    assert parse_long_timeout_end("60d", now) == now + datetime.timedelta(days=60)


def test_parse_long_timeout_end_iso8601():
    now = datetime.datetime(2026, 6, 2, 10, 0, 0, tzinfo=datetime.timezone.utc)

    assert parse_long_timeout_end("2026-08-01T12:34:56Z", now) == datetime.datetime(
        2026, 8, 1, 12, 34, 56, tzinfo=datetime.timezone.utc
    )


def test_parse_long_timeout_end_rejects_invalid_values():
    now = datetime.datetime(2026, 6, 2, 10, 0, 0, tzinfo=datetime.timezone.utc)

    assert parse_long_timeout_end("", now) is None
    assert parse_long_timeout_end("0s", now) is None
    assert parse_long_timeout_end("definitely-not-a-time", now) is None


def test_get_long_timeout_duration_seconds_caps_to_twitch_limit():
    now = datetime.datetime(2026, 6, 2, 10, 0, 0, tzinfo=datetime.timezone.utc)
    timeout_end = now + datetime.timedelta(days=60)

    assert get_long_timeout_duration_seconds(timeout_end, now) == TWITCH_MAX_TIMEOUT_SECONDS


def test_parse_twitch_timeout_end_accepts_helix_timestamp():
    assert parse_twitch_timeout_end("2026-08-01T12:34:56Z") == datetime.datetime(
        2026, 8, 1, 12, 34, 56, tzinfo=datetime.timezone.utc
    )


def test_format_timeout_end_strips_microseconds():
    timeout_end = datetime.datetime(2026, 8, 1, 12, 34, 56, 123456, tzinfo=datetime.timezone.utc)

    assert format_timeout_end(timeout_end) == "2026-08-01T12:34:56+00:00"


def test_long_timeout_reason_uses_formatted_timeout_end():
    timeout_end = datetime.datetime(2026, 8, 1, 12, 34, 56, 123456, tzinfo=datetime.timezone.utc)

    assert long_timeout_reason(timeout_end) == "Long timeout active until 2026-08-01T12:34:56+00:00"


def test_apply_long_timeout_calls_bot_timeout(monkeypatch):
    now = datetime.datetime(2026, 6, 2, 10, 0, 0, tzinfo=datetime.timezone.utc)
    timeout_end = now + datetime.timedelta(days=1)
    bot = Mock()
    user = object()

    monkeypatch.setattr("pajbot.modules.longtimeout.utils.now", lambda: now)

    apply_long_timeout(bot, user, timeout_end)

    bot.timeout.assert_called_once_with(user, 86400, reason="Long timeout active until 2026-06-03T10:00:00+00:00")


def test_apply_long_timeout_skips_non_positive_duration(monkeypatch):
    now = datetime.datetime(2026, 6, 2, 10, 0, 0, tzinfo=datetime.timezone.utc)
    timeout_end = now - datetime.timedelta(seconds=1)
    bot = Mock()

    monkeypatch.setattr("pajbot.modules.longtimeout.utils.now", lambda: now)

    apply_long_timeout(bot, object(), timeout_end)

    bot.timeout.assert_not_called()


def make_bot_with_ban_data(ban_data):
    helix_api = SimpleNamespace(get_banned_user=Mock(return_value=ban_data))
    return SimpleNamespace(
        twitch_helix_api=helix_api,
        streamer=SimpleNamespace(id="streamer-id"),
        streamer_access_token_manager=object(),
    )


def make_http_error(status_code=500, text="server error"):
    response = Response()
    response.status_code = status_code
    response._content = text.encode()
    return HTTPError(response=response)


def test_should_refresh_long_timeout_when_not_banned(monkeypatch):
    now = datetime.datetime(2026, 6, 2, 10, 0, 0, tzinfo=datetime.timezone.utc)
    timeout_end = now + datetime.timedelta(days=30)
    bot = make_bot_with_ban_data(None)
    user = SimpleNamespace(id="123")

    monkeypatch.setattr("pajbot.modules.longtimeout.utils.now", lambda: now)

    assert should_refresh_long_timeout(bot, user, timeout_end) is True


def test_should_refresh_long_timeout_when_current_timeout_near_expiry(monkeypatch):
    now = datetime.datetime(2026, 6, 2, 10, 0, 0, tzinfo=datetime.timezone.utc)
    ban_data = SimpleNamespace(expires_at="2026-06-02T10:04:59Z")
    bot = make_bot_with_ban_data(ban_data)
    user = SimpleNamespace(id="123")

    monkeypatch.setattr("pajbot.modules.longtimeout.utils.now", lambda: now)

    assert should_refresh_long_timeout(bot, user, now + datetime.timedelta(days=30)) is True


def test_should_refresh_long_timeout_when_current_timeout_is_far_enough(monkeypatch):
    now = datetime.datetime(2026, 6, 2, 10, 0, 0, tzinfo=datetime.timezone.utc)
    ban_data = SimpleNamespace(expires_at="2026-06-02T10:05:01Z")
    bot = make_bot_with_ban_data(ban_data)
    user = SimpleNamespace(id="123")

    monkeypatch.setattr("pajbot.modules.longtimeout.utils.now", lambda: now)

    assert should_refresh_long_timeout(bot, user, now + datetime.timedelta(days=30)) is False


def test_should_refresh_long_timeout_returns_false_on_http_error(caplog):
    bot = make_bot_with_ban_data(None)
    bot.twitch_helix_api.get_banned_user.side_effect = make_http_error()
    user = SimpleNamespace(id="123")
    timeout_end = datetime.datetime(2026, 7, 2, 10, 0, 0, tzinfo=datetime.timezone.utc)

    assert should_refresh_long_timeout(bot, user, timeout_end) is False
    assert "Failed to fetch long timeout state for user 123" in caplog.text


def test_should_refresh_long_timeout_reraises_http_error_without_response():
    bot = make_bot_with_ban_data(None)
    bot.twitch_helix_api.get_banned_user.side_effect = HTTPError("boom")
    user = SimpleNamespace(id="123")
    timeout_end = datetime.datetime(2026, 7, 2, 10, 0, 0, tzinfo=datetime.timezone.utc)

    with pytest.raises(HTTPError):
        should_refresh_long_timeout(bot, user, timeout_end)


def test_load_commands_registers_longtimeout_commands():
    module = LongTimeoutModule(None)
    module.load_commands()

    assert "longtimeout" in module.commands
    assert "unlongtimeout" in module.commands


def test_on_message_clears_expired_timeout(monkeypatch):
    now = datetime.datetime(2026, 6, 2, 10, 0, 0, tzinfo=datetime.timezone.utc)
    module = LongTimeoutModule(None)
    source = SimpleNamespace(long_timeout_end=now - datetime.timedelta(seconds=1))

    monkeypatch.setattr("pajbot.modules.longtimeout.utils.now", lambda: now)

    assert module.on_message(source, whisper=False) is True
    assert source.long_timeout_end is None


def test_on_message_reapplies_active_timeout(monkeypatch):
    now = datetime.datetime(2026, 6, 2, 10, 0, 0, tzinfo=datetime.timezone.utc)
    timeout_end = now + datetime.timedelta(days=1)
    module = LongTimeoutModule(SimpleNamespace())
    source = SimpleNamespace(long_timeout_end=timeout_end)
    apply_mock = Mock()

    monkeypatch.setattr("pajbot.modules.longtimeout.utils.now", lambda: now)
    monkeypatch.setattr("pajbot.modules.longtimeout.apply_long_timeout", apply_mock)

    assert module.on_message(source, whisper=False) is True
    apply_mock.assert_called_once_with(module.bot, source, timeout_end)


class FakeQuery:
    def __init__(self, users):
        self.users = users

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return list(self.users)


class FakeSession:
    def __init__(self, users):
        self.users = users

    def query(self, model):
        return FakeQuery(self.users)


@contextmanager
def fake_session_scope(users):
    yield FakeSession(users)


def test_on_tick_updates_expired_and_refreshes_active_timeouts(monkeypatch):
    now = datetime.datetime(2026, 6, 2, 10, 0, 0, tzinfo=datetime.timezone.utc)
    expired_user = SimpleNamespace(long_timeout_end=now - datetime.timedelta(seconds=1))
    active_user = SimpleNamespace(long_timeout_end=now + datetime.timedelta(days=1))
    module = LongTimeoutModule(SimpleNamespace())
    module.last_long_timeout_check = now - datetime.timedelta(minutes=1)
    apply_mock = Mock()
    refresh_mock = Mock(return_value=True)

    monkeypatch.setattr("pajbot.modules.longtimeout.utils.now", lambda: now)
    monkeypatch.setattr(
        "pajbot.modules.longtimeout.DBManager.create_session_scope",
        lambda: fake_session_scope([expired_user, active_user]),
    )
    monkeypatch.setattr("pajbot.modules.longtimeout.apply_long_timeout", apply_mock)
    monkeypatch.setattr("pajbot.modules.longtimeout.should_refresh_long_timeout", refresh_mock)

    assert module.on_tick() is True
    assert expired_user.long_timeout_end is None
    refresh_mock.assert_called_once_with(module.bot, active_user, active_user.long_timeout_end)
    apply_mock.assert_called_once_with(module.bot, active_user, active_user.long_timeout_end)


def test_on_tick_skips_when_interval_not_elapsed(monkeypatch):
    now = datetime.datetime(2026, 6, 2, 10, 0, 0, tzinfo=datetime.timezone.utc)
    module = LongTimeoutModule(SimpleNamespace())
    module.last_long_timeout_check = now
    create_session_scope = Mock()

    monkeypatch.setattr("pajbot.modules.longtimeout.utils.now", lambda: now)
    monkeypatch.setattr("pajbot.modules.longtimeout.DBManager.create_session_scope", create_session_scope)

    assert module.on_tick() is True
    create_session_scope.assert_not_called()
