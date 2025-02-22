from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class NullAction(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class MessageAction(_message.Message):
    __slots__ = ("message",)
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    message: str
    def __init__(self, message: _Optional[str] = ...) -> None: ...

class WhisperAction(_message.Message):
    __slots__ = ("target_user_id", "message", "delay")
    TARGET_USER_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    DELAY_FIELD_NUMBER: _ClassVar[int]
    target_user_id: str
    message: str
    delay: int
    def __init__(self, target_user_id: _Optional[str] = ..., message: _Optional[str] = ..., delay: _Optional[int] = ...) -> None: ...

class AnnounceAction(_message.Message):
    __slots__ = ("message",)
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    message: str
    def __init__(self, message: _Optional[str] = ...) -> None: ...

class DeleteMessageAction(_message.Message):
    __slots__ = ("target_message_id",)
    TARGET_MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    target_message_id: str
    def __init__(self, target_message_id: _Optional[str] = ...) -> None: ...

class TimeoutAction(_message.Message):
    __slots__ = ("target_user_id", "duration", "reason")
    TARGET_USER_ID_FIELD_NUMBER: _ClassVar[int]
    DURATION_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    target_user_id: str
    duration: int
    reason: str
    def __init__(self, target_user_id: _Optional[str] = ..., duration: _Optional[int] = ..., reason: _Optional[str] = ...) -> None: ...

class BanAction(_message.Message):
    __slots__ = ("target_user_id", "reason")
    TARGET_USER_ID_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    target_user_id: str
    reason: str
    def __init__(self, target_user_id: _Optional[str] = ..., reason: _Optional[str] = ...) -> None: ...

class UnbanAction(_message.Message):
    __slots__ = ("target_user_id",)
    TARGET_USER_ID_FIELD_NUMBER: _ClassVar[int]
    target_user_id: str
    def __init__(self, target_user_id: _Optional[str] = ...) -> None: ...

class TwitchChatMessageRequest(_message.Message):
    __slots__ = ("broadcaster_user_id", "broadcaster_user_login", "broadcaster_user_name", "chatter_user_id", "chatter_user_login", "chatter_user_name", "event_json")
    BROADCASTER_USER_ID_FIELD_NUMBER: _ClassVar[int]
    BROADCASTER_USER_LOGIN_FIELD_NUMBER: _ClassVar[int]
    BROADCASTER_USER_NAME_FIELD_NUMBER: _ClassVar[int]
    CHATTER_USER_ID_FIELD_NUMBER: _ClassVar[int]
    CHATTER_USER_LOGIN_FIELD_NUMBER: _ClassVar[int]
    CHATTER_USER_NAME_FIELD_NUMBER: _ClassVar[int]
    EVENT_JSON_FIELD_NUMBER: _ClassVar[int]
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    chatter_user_id: str
    chatter_user_login: str
    chatter_user_name: str
    event_json: str
    def __init__(self, broadcaster_user_id: _Optional[str] = ..., broadcaster_user_login: _Optional[str] = ..., broadcaster_user_name: _Optional[str] = ..., chatter_user_id: _Optional[str] = ..., chatter_user_login: _Optional[str] = ..., chatter_user_name: _Optional[str] = ..., event_json: _Optional[str] = ...) -> None: ...

class Meta(_message.Message):
    __slots__ = ("comments",)
    COMMENTS_FIELD_NUMBER: _ClassVar[int]
    comments: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, comments: _Optional[_Iterable[str]] = ...) -> None: ...

class AnyAction(_message.Message):
    __slots__ = ("message", "whisper", "announce", "delete_message", "timeout", "ban", "unban")
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    WHISPER_FIELD_NUMBER: _ClassVar[int]
    ANNOUNCE_FIELD_NUMBER: _ClassVar[int]
    DELETE_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    BAN_FIELD_NUMBER: _ClassVar[int]
    UNBAN_FIELD_NUMBER: _ClassVar[int]
    message: MessageAction
    whisper: WhisperAction
    announce: AnnounceAction
    delete_message: DeleteMessageAction
    timeout: TimeoutAction
    ban: BanAction
    unban: UnbanAction
    def __init__(self, message: _Optional[_Union[MessageAction, _Mapping]] = ..., whisper: _Optional[_Union[WhisperAction, _Mapping]] = ..., announce: _Optional[_Union[AnnounceAction, _Mapping]] = ..., delete_message: _Optional[_Union[DeleteMessageAction, _Mapping]] = ..., timeout: _Optional[_Union[TimeoutAction, _Mapping]] = ..., ban: _Optional[_Union[BanAction, _Mapping]] = ..., unban: _Optional[_Union[UnbanAction, _Mapping]] = ...) -> None: ...

class TwitchChatMessageReply(_message.Message):
    __slots__ = ("meta", "actions")
    META_FIELD_NUMBER: _ClassVar[int]
    ACTIONS_FIELD_NUMBER: _ClassVar[int]
    meta: Meta
    actions: _containers.RepeatedCompositeFieldContainer[AnyAction]
    def __init__(self, meta: _Optional[_Union[Meta, _Mapping]] = ..., actions: _Optional[_Iterable[_Union[AnyAction, _Mapping]]] = ...) -> None: ...
