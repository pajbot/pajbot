import math


def time_since(t1, t2, time_format="long"):
    time_diff = t1 - t2
    if time_format == "long":
        num_dict = ["year", "month", "day", "hour", "minute", "second"]
    else:
        num_dict = ["y", "M", "d", "h", "m", "s"]
    num = [
        math.trunc(time_diff / 31536000),
        math.trunc(time_diff / 2628000 % 12),
        math.trunc(time_diff / 86400 % 30.41666666666667),
        math.trunc(time_diff / 3600 % 24),
        math.trunc(time_diff / 60 % 60),
        round(time_diff % 60, 1),
    ]

    i = 0
    j = 0
    time_arr = []
    while i < 2 and j < 6:
        if num[j] > 0:
            if time_format == "long":
                time_arr.append("{0:g} {1}{2}".format(num[j], num_dict[j], "s" if num[j] > 1 else ""))
            else:
                time_arr.append("{}{}".format(num[j], num_dict[j]))
            i += 1
        j += 1

    if time_format == "long":
        return " and ".join(time_arr)

    return "".join(time_arr)
