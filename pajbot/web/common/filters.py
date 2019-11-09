import pajbot.utils
from jinja2 import Markup


def is_naive_datetime(dt):
    return dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None


def init(app):
    @app.template_filter()
    def date_format(value, format="full"):
        if format == "full":
            date_format = "%Y-%m-%d %H:%M:%S"

        return value.strftime(date_format)

    @app.template_filter("strftime")
    def time_strftime(value, format):
        return value.strftime(format)

    @app.template_filter("localize")
    def time_localize(value, format="LLL"):
        if is_naive_datetime(value):
            raise ValueError("Cannot localize datetime without timezone info")

        milliseconds_since_utc_epoch = value.timestamp() * 1000

        # fallback_format is for users with JavaScript disabled
        fallback_format = str(value)

        return Markup(
            f'<span class="localized-datetime" data-timestamp="{milliseconds_since_utc_epoch}" data-format="{format}">{fallback_format}</span>'
        )

    @app.template_filter("unix_timestamp")
    def time_unix_timestamp(value):
        return value.timestamp()

    @app.template_filter()
    def number_format(value, tsep=",", dsep="."):
        s = str(value)
        cnt = 0
        numchars = dsep + "0123456789"
        ls = len(s)
        while cnt < ls and s[cnt] not in numchars:
            cnt += 1

        lhs = s[:cnt]
        s = s[cnt:]
        if not dsep:
            cnt = -1
        else:
            cnt = s.rfind(dsep)
        if cnt > 0:
            rhs = dsep + s[cnt + 1 :]
            s = s[:cnt]
        else:
            rhs = ""

        splt = ""
        while s != "":
            splt = s[-3:] + tsep + splt
            s = s[:-3]

        return lhs + splt[:-1] + rhs

    @app.template_filter("time_ago")
    def time_ago(t, time_format="long"):
        return pajbot.utils.time_ago(t, time_format=time_format)

    @app.template_filter("format_timedelta")
    def format_timedelta(t, time_format="long"):
        v = pajbot.utils.time_since(t.total_seconds(), 0, time_format=time_format)
        return "None" if len(v) == 0 else v

    @app.template_filter("time_diff")
    def time_diff(t1, t2, time_format="long"):
        return pajbot.utils.time_since(t1.timestamp(), t2.timestamp(), time_format=time_format)

    @app.template_filter("time_ago_timespan_seconds")
    def time_ago_timespan_seconds(t, time_format="long"):
        v = pajbot.utils.time_since(t, 0, time_format=time_format)
        return "None" if len(v) == 0 else v

    @app.template_filter("seconds_to_vodtime")
    def seconds_to_vodtime(t):
        s = int(t)
        h = s / 3600
        m = s % 3600 / 60
        s = s % 60
        return "%dh%02dm%02ds" % (h, m, s)

    @app.template_filter("with_unit")
    def with_unit(value, unit, plural_suffix="s"):
        """with_unit ≙ value_with_pluralized_unit"""
        if value == 1:
            return f"{value} {unit}"  # e.g. 1 point
        else:
            return f"{value} {unit}{plural_suffix}"  # e.g. 2 points
