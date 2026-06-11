from typing import Optional, TypedDict


class ChunkWithPrefix(TypedDict):
    prefix: str
    parts: list[str]


def _build_message_suffix(
    current_prefix: Optional[str], prefix: str, part: str, separator: str, *, has_message: bool
) -> str:
    needs_prefix = current_prefix != prefix
    suffix = f"{prefix}{separator}{part}" if needs_prefix else part

    if has_message:
        suffix = f"{separator}{suffix}"

    return suffix


def _append_part_to_message(
    current_message: str, current_prefix: Optional[str], prefix: str, part: str, separator: str, limit: int
) -> tuple[str, str]:
    suffix = _build_message_suffix(
        current_prefix,
        prefix,
        part,
        separator,
        has_message=bool(current_message),
    )

    if len(current_message) + len(suffix) > limit:
        raise ValueError("Part does not fit in the message limit")

    return current_message + suffix, prefix


def split_into_chunks_with_prefix(
    chunks: list[ChunkWithPrefix],
    separator: str = " ",
    limit: int = 500,
    default: Optional[str] = None,
) -> list[str]:
    messages: list[str] = []
    current_message = ""
    current_prefix: Optional[str] = None

    for chunk in chunks:
        prefix = chunk["prefix"]
        parts = chunk["parts"]
        for part in parts:
            try:
                current_message, current_prefix = _append_part_to_message(
                    current_message, current_prefix, prefix, part, separator, limit
                )
            except ValueError as e:
                if not current_message:
                    raise ValueError("Function was given part that could never fit") from e

                messages.append(current_message)
                current_message, current_prefix = _append_part_to_message("", None, prefix, part, separator, limit)

    if current_message:
        messages.append(current_message)

    if not messages and default is not None:
        messages = [default]

    return messages
