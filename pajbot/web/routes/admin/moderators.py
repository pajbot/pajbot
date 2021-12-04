import collections

from pajbot.managers.db import DBManager
from pajbot.models.user import User
from pajbot.web.utils import requires_level

from flask import render_template
from flask.typing import ResponseReturnValue


def init(page) -> None:
    @page.route("/moderators/")
    @requires_level(500)
    def moderators(**options) -> ResponseReturnValue:
        with DBManager.create_session_scope() as db_session:
            moderator_users = db_session.query(User).filter(User.level > 100).order_by(User.level.desc()).all()
            userlists = collections.OrderedDict()
            userlists["Admins"] = list(filter(lambda user: user.level >= 2000, moderator_users))
            userlists["Super Moderators"] = list(filter(lambda user: 1000 <= user.level < 1999, moderator_users))
            userlists["Moderators"] = list(filter(lambda user: 500 <= user.level < 1000, moderator_users))
            userlists["Notables/Helpers"] = list(filter(lambda user: 101 <= user.level < 500, moderator_users))
            return render_template("admin/moderators.html", userlists=userlists)
