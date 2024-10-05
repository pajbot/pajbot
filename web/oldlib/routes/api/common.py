from flask import Blueprint, redirect


def init(bp: Blueprint) -> None:
    @bp.route("/test")
    def test():
        return redirect("/commands", 303)
