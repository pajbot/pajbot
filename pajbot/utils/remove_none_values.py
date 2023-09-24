from typing import Any


def remove_none_values(d: dict[Any, Any]) -> dict[Any, Any]:
    return {k: v for k, v in d.items() if v is not None}
