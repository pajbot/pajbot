import pajbot.web.utils
from pajbot.managers.db import DBManager
from pajbot.models.duel import UserDuelStats
from pajbot.models.user import User

from flask import render_template


def init(app):
    @app.route("/stats")
    def stats():
        bot_commands_list = pajbot.web.utils.get_cached_commands()
        top_100_emotes = pajbot.web.utils.get_top_emotes()
        top_5_commands = sorted(
            bot_commands_list, key=lambda c: c["data"]["num_uses"] if c["data"] is not None else -1, reverse=True
        )[:5]

        # TODO: Make this hideable through some magic setting (NOT config.ini @_@)
        with DBManager.create_session_scope() as db_session:
            top_5_line_farmers = db_session.query(User).order_by(User.num_lines.desc()).limit(5).all()
            return render_template(
                "stats.html",
                top_5_commands=top_5_commands,
                top_5_line_farmers=top_5_line_farmers,
                top_100_emotes=top_100_emotes,
            )

    @app.route("/stats/duels")
    def stats_duels():
        with DBManager.create_session_scope() as db_session:

            data = {
                "top_5_winners": db_session.query(UserDuelStats).order_by(UserDuelStats.duels_won.desc())[:5],
                "top_5_points_won": db_session.query(UserDuelStats).order_by(UserDuelStats.profit.desc())[:5],
                "top_5_points_lost": db_session.query(UserDuelStats).order_by(UserDuelStats.profit.asc())[:5],
                "top_5_losers": db_session.query(UserDuelStats).order_by(UserDuelStats.duels_lost.desc())[:5],
                "top_5_winrate": db_session.query(UserDuelStats)
                .filter(UserDuelStats.duels_won >= 5)
                .order_by(UserDuelStats.winrate.desc())
                .order_by(UserDuelStats.duels_won.desc())[:5],
                "bottom_5_winrate": db_session.query(UserDuelStats)
                .filter(UserDuelStats.duels_lost >= 5)
                .order_by(UserDuelStats.winrate.asc())
                .order_by(UserDuelStats.duels_won.asc())[:5],
            }

            return render_template("stats_duels.html", **data)
