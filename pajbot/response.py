from __future__ import annotations
import logging
from dataclasses import dataclass, field

from pajbot.models.user import User

log = logging.getLogger(__name__)

type CommandResponse = tuple[list[AnyResponse], bool]


def silent_fail() -> CommandResponse:
    return ([], False)


def silent_success() -> CommandResponse:
    return ([], True)


def reply_to_user(
    method: str,
    user: User,
    message: str,
    message_id: str | None,
    is_whisper: bool,
    check_msg: bool,
) -> list[AnyResponse]:
    """

    Keyword arguments:
    check_msg -- indicates whether the message should be run through the is_bad_message check before being sent (default False)
    """

    # TODO: Re-implement banphrase check

    match method:
        case "say":
            return SayResponse.one(f"@{user.name}, {message}")

        case "whisper":
            return WhisperResponse.one(user.id, message)

        case "me":
            return MeResponse.one(f"@{user.name}, {message}")

        case "reply":
            if is_whisper:
                return WhisperResponse.one(user.id, message)
            else:
                return SayResponse.one(f"@{user.name}, {message}", msg_id=message_id)

        case _:
            log.warning("Unknown send_message method: %s", method)

    return []


def fail_reply_to_user(
    method: str,
    user: User,
    message: str,
    message_id: str | None,
    is_whisper: bool,
    check_msg: bool,
) -> CommandResponse:
    """

    Keyword arguments:
    check_msg -- indicates whether the message should be run through the is_bad_message check before being sent (default False)
    """

    # TODO: Re-implement banphrase check

    response = []

    match method:
        case "say":
            response = SayResponse.one(f"@{user.name}, {message}")

        case "whisper":
            response = WhisperResponse.one(user.id, message)

        case "me":
            response = MeResponse.one(f"@{user.name}, {message}")

        case "reply":
            if is_whisper:
                response = WhisperResponse.one(user.id, message)
            else:
                response = SayResponse.one(f"@{user.name}, {message}", msg_id=message_id)

        case _:
            log.warning("Unknown send_message method: %s", method)

    return (response, True)


@dataclass
class DeleteMessageResponse:
    msg_id: str


@dataclass
class TimeoutResponse:
    target_user_id: str
    duration: int
    reason: str | None = None

    @staticmethod
    def one(
        target_user_id: str,
        duration: int,
        reason: str | None = None,
    ) -> list[AnyResponse]:
        return [
            TimeoutResponse(
                target_user_id,
                duration,
                reason,
            )
        ]


@dataclass
class BanResponse:
    target_user_id: str
    reason: str | None = None


@dataclass
class UnbanResponse:
    target_user_id: str


@dataclass
class SayResponse:
    message: str
    # for use in replies
    msg_id: str | None = None

    @staticmethod
    def one(message: str, msg_id: str | None = None) -> list[AnyResponse]:
        return [
            SayResponse(
                message,
                msg_id=msg_id,
            )
        ]


@dataclass
class MeResponse:
    message: str

    @staticmethod
    def one(message: str) -> list[AnyResponse]:
        return [
            MeResponse(
                message,
            )
        ]

    @staticmethod
    def success(message: str) -> CommandResponse:
        return (
            [
                MeResponse(message),
            ],
            True,
        )

    @staticmethod
    def fail(message: str) -> CommandResponse:
        return (
            [
                MeResponse(message),
            ],
            False,
        )


@dataclass
class WhisperResponse:
    target_user_id: str
    message: str
    delay: int = 0

    @staticmethod
    def one(target_user_id: str, message: str, delay: int = 0) -> list[AnyResponse]:
        return [
            WhisperResponse(
                target_user_id,
                message,
                delay,
            )
        ]

    @staticmethod
    def success(target_user_id: str, message: str, delay: int = 0) -> CommandResponse:
        return (
            [
                WhisperResponse(
                    target_user_id,
                    message,
                    delay,
                ),
            ],
            True,
        )

    @staticmethod
    def fail(target_user_id: str, message: str, delay: int = 0) -> CommandResponse:
        return (
            [
                WhisperResponse(
                    target_user_id,
                    message,
                    delay,
                )
            ],
            False,
        )


@dataclass
class AnnounceResponse:
    message: str


type AnyResponse = (
    TimeoutResponse
    | BanResponse
    | UnbanResponse
    | DeleteMessageResponse
    | SayResponse
    | MeResponse
    | WhisperResponse
    | AnnounceResponse
)


@dataclass
class ResponseMeta:
    comments: list[str] = field(default_factory=list)

    def has_data(self) -> bool:
        if self.comments:
            return True

        return False

    def add(self, comment_source: str, comment: str) -> None:
        self.comments.append(f"[{comment_source}]: {comment}")


@dataclass
class HandlerResponse:
    stop: bool = False
    actions: list[AnyResponse] = field(default_factory=list)

    @staticmethod
    def null() -> "HandlerResponse":
        return HandlerResponse()

    @staticmethod
    def do_say(message: str) -> HandlerResponse:
        res = HandlerResponse()
        res.say(
            message,
        )
        return res

    def say(self, message: str) -> None:
        self.actions.append(
            SayResponse(
                message,
            )
        )

    @staticmethod
    def do_me(message: str) -> HandlerResponse:
        res = HandlerResponse()
        res.me(
            message,
        )
        return res

    def me(self, message: str) -> None:
        self.actions.append(
            MeResponse(
                message,
            )
        )

    def whisper(self, target_user_id: str, message: str, delay: int = 0) -> None:
        self.actions.append(
            WhisperResponse(
                target_user_id,
                message,
                delay=delay,
            )
        )

    @staticmethod
    def do_timeout(
        target_user_id: str,
        duration: int,
        reason: str | None = None,
    ) -> HandlerResponse:
        res = HandlerResponse()
        res.timeout(
            target_user_id,
            duration,
            reason=reason,
        )
        return res

    def timeout(
        self,
        target_user_id: str,
        duration: int,
        reason: str | None = None,
    ) -> None:
        self.stop = True

        self.actions.append(
            TimeoutResponse(
                target_user_id,
                duration,
                reason=reason,
            )
        )

    @staticmethod
    def do_delete_or_timeout(
        target_user_id: str,
        moderation_action: str,
        msg_id: str,
        duration: int,
        reason: str | None = None,
        disable_warnings: bool = False,
    ) -> HandlerResponse:
        res = HandlerResponse()
        res.delete_or_timeout(
            target_user_id,
            moderation_action,
            msg_id,
            duration,
            reason=reason,
            disable_warnings=disable_warnings,
        )
        return res

    def delete_or_timeout(
        self,
        target_user_id: str,
        moderation_action: str,
        msg_id: str,
        duration: int,
        reason: str | None = None,
        disable_warnings: bool = False,
    ) -> None:
        self.stop = True

        match moderation_action.lower():
            case "delete":
                self.actions.append(
                    DeleteMessageResponse(
                        msg_id,
                    )
                )

            case "timeout":
                if disable_warnings:
                    self.actions.append(
                        TimeoutResponse(
                            target_user_id,
                            duration,
                            reason,
                        )
                    )
                else:
                    # TODO: Support warns?
                    self.actions.append(
                        TimeoutResponse(
                            target_user_id,
                            duration,
                            reason,
                        )
                    )

            case unhandled:
                raise ValueError(
                    f"moderation_action {unhandled} is supported, it must be either 'delete' or 'timeout'!"
                )

    def override(self, other: "HandlerResponse") -> None:
        for action in other.actions:
            match action:
                case BanResponse():
                    # TODO: If it's a timeout or ban, we should look through our current
                    # actions & override if it's bigger
                    self.actions.append(action)

                case TimeoutResponse():
                    # TODO: If it's a timeout or ban, we should look through our current
                    # actions & override if it's bigger
                    self.actions.append(action)

                case _:
                    self.actions.append(action)
