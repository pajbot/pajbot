def seconds_conversion(self, value: int, unit: str="second"):
    unit = unit.lower()

    if unit.endswith(s):
        unit = unit[:-1]

    if unit == "second":
        return value

    if unit == "minute":
        return value * 60

    if unit == "hour":
        return value * 3600

    if unit == "day":
        return value * 86400

    if unit == "week":
        return value * 604800

    if unit == "month":
        return value * 2629746
