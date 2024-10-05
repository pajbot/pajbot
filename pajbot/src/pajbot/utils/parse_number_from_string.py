from typing import Union


def parse_number_from_string(var: str) -> Union[int, float]:
    """Tries to parse a number (int or float) from the given string.
    If no easy conversion could be made, raise a ValueError."""

    try:
        return int(var)
    except ValueError:
        pass

    try:
        return float(var)
    except ValueError:
        pass

    raise ValueError(f"could not convert string to number using int() or float(): {var}")
