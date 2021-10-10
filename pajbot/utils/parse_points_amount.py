from __future__ import annotations

from typing import TYPE_CHECKING

import math

from pajbot.exc import InvalidPointAmount

if TYPE_CHECKING:
    from pajbot.models.user import User

ALLIN_PHRASES = {"all", "allin"}


def parse_points_amount(user: User, point_string: str) -> int:
    if point_string.startswith("0b"):
        try:
            bet = int(point_string, 2)

            return bet
        except (ValueError, TypeError):
            raise InvalidPointAmount("Invalid binary format (example: 0b101)")
    elif point_string.startswith("0x"):
        try:
            bet = int(point_string, 16)

            return bet
        except (ValueError, TypeError):
            raise InvalidPointAmount("Invalid hex format (example: 0xFF)")
    elif point_string.endswith("%"):
        try:
            percentage = float(point_string[:-1])
            if percentage <= 0 or percentage > 100:
                raise InvalidPointAmount("Invalid percentage format (example: 43.5%) :o")

            return math.floor(user.points * (percentage / 100))
        except (ValueError, TypeError):
            raise InvalidPointAmount("Invalid percentage format (example: 43.5%)")
    elif point_string[0].isnumeric():
        try:
            point_string = point_string.lower()
            num_k = point_string.count("k")
            num_m = point_string.count("m")
            point_string = point_string.replace("k", "")
            point_string = point_string.replace("m", "")
            bet_f = float(point_string)

            if num_k:
                bet_f *= 1000 ** num_k
            if num_m:
                bet_f *= 1000000 ** num_m

            return round(bet_f)
        except (ValueError, TypeError):
            raise InvalidPointAmount("Non-recognizable point amount (examples: 100, 10k, 1m, 0.5k)")
    elif point_string.lower() in ALLIN_PHRASES:
        return user.points

    raise InvalidPointAmount("Invalid point amount (examples: 100, 10k, 1m, 0.5k)")
