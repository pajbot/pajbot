import pajbot.web.utils

from flask import Blueprint, redirect


def init(bp: Blueprint) -> None:
    pajbot.web.utils.init_json_serializer(bp)

    @bp.route("/test")
    def test():
        return redirect("/commands", 303)
