import logging
import json

from flask import render_template
from flask import session
from flask import redirect

from pajbot.managers.db import DBManager
from pajbot.models.roulette import Roulette
from pajbot.models.user import User
from pajbot.models.user_connection import UserConnections
from pajbot.managers.redis import RedisManager

log = logging.getLogger(__name__)


def init(app):
    @app.route("/user/<login>")
    def user_profile(login):
        with DBManager.create_session_scope() as db_session:
            user = User.find_by_user_input(db_session, login)
            if user is None:
                return render_template("no_user.html"), 404

            roulettes = db_session.query(Roulette).filter_by(user_id=user.id).order_by(Roulette.created_at.desc()).all()

            roulette_stats = None
            if len(roulettes) > 0:
                profit = 0
                total_points = 0
                biggest_loss = 0
                biggest_win = 0
                biggest_winstreak = 0
                biggest_losestreak = 0
                num_wins = 0
                num_losses = 0
                winrate = 0
                num_roulettes = len(roulettes)
                cw = 0
                for roulette in roulettes:
                    profit += roulette.points
                    total_points += abs(roulette.points)

                    if roulette.points > 0:
                        # a win!
                        num_wins += 1
                        if cw < 0:
                            if abs(cw) > biggest_losestreak:
                                biggest_losestreak = abs(cw)
                            cw = 0
                        cw += 1
                    else:
                        # a loss
                        num_losses += 1
                        if cw > 0:
                            if cw > biggest_winstreak:
                                biggest_winstreak = cw
                            cw = 0
                        cw -= 1

                    if roulette.points < biggest_loss:
                        biggest_loss = roulette.points
                    elif roulette.points > biggest_win:
                        biggest_win = roulette.points

                # Calculate winrate
                if num_losses == 0:
                    winrate = 1
                elif num_wins == 0:
                    winrate = 0
                else:
                    winrate = num_wins / num_roulettes

                # Finalize win/lose streaks in case we're currently
                # on the biggest win/lose streak
                if cw < 0:
                    if abs(cw) > biggest_losestreak:
                        biggest_losestreak = abs(cw)
                elif cw > 0:
                    if cw > biggest_winstreak:
                        biggest_winstreak = cw

                if "roulette" in app.module_manager:
                    roulette_base_winrate = 1.0 - app.module_manager["roulette"].settings["rigged_percentage"] / 100
                else:
                    roulette_base_winrate = 0.45

                roulette_stats = {
                    "profit": profit,
                    "total_points": total_points,
                    "biggest_win": biggest_win,
                    "biggest_loss": biggest_loss,
                    "num_roulettes": num_roulettes,
                    "biggest_winstreak": biggest_winstreak,
                    "biggest_losestreak": biggest_losestreak,
                    "winrate": winrate,
                    "winrate_str": f"{winrate * 100:.2f}%",
                    "roulette_base_winrate": roulette_base_winrate,
                }
            paired = bool(UserConnections._from_twitch_id(db_session, user.id))
            return render_template(
                "user.html", user=user, roulette_stats=roulette_stats, roulettes=roulettes, paired=paired
            )

    @app.route("/connections")
    def user_profile_connections():
        with DBManager.create_session_scope() as db_session:
            if "user" not in session:
                return redirect(f"/login?n=/connections/")

            user = User.find_by_id(db_session, session["user"]["id"])
            if user is None:
                return render_template("no_user.html"), 404
            user_connection = UserConnections._from_twitch_id(db_session, user.id)
            discord = None
            steam = None
            if (
                "discord_id" in session
                and "discord_username" in session
                and session["discord_id"] is not None
                and session["discord_username"] is not None
            ):
                discord = {"id": session["discord_id"], "username": session["discord_username"]}
            if "steam_id" in session and session["steam_id"] is not None:
                steam = {"id": session["steam_id"]}

            data = {"steam": steam, "discord": discord, "twitch": session["user"], "offcd": user.offcd}
            user_connection = UserConnections._from_twitch_id(db_session, user.id)
            if user_connection:
                return render_template(
                    "connections_unlink.html",
                    user=user,
                    data=user_connection.jsonify(),
                    twitch_user=session["user"],
                    returnUrl=f"/connections",
                )
            return render_template(
                "connections.html", user=user, data=data, returnUrl=f"/connections", pair_failed=False
            )

    @app.route("/connections/pair")
    def user_profile_connections_pair():
        with DBManager.create_session_scope() as db_session:
            if "user" not in session:
                return redirect(f"/login?n=/connections/")

            user = User.find_by_id(db_session, session["user"]["id"])
            if user is None:
                return render_template("no_user.html"), 404
            if user.offcd:
                discord = None
                steam = None
                if (
                    "discord_id" in session
                    and "discord_username" in session
                    and session["discord_id"] is not None
                    and session["discord_username"] is not None
                ):
                    discord = {"id": session["discord_id"], "username": session["discord_username"]}
                if "steam_id" in session and session["steam_id"] is not None:
                    steam = {"id": session["steam_id"]}

                data = {"steam": steam, "discord": discord, "twitch": session["user"], "offcd": user.offcd}
                try:
                    if discord is not None and steam is not None:
                        UserConnections._create(
                            db_session,
                            twitch_id=session["user"]["id"],
                            twitch_login=user.login,
                            discord_user_id=session["discord_id"],
                            discord_username=session["discord_username"],
                            steam_id=session["steam_id"],
                        )
                        user._setcd(db_session)
                        db_session.commit()
                        return redirect(f"/connections/")
                    else:
                        return render_template(
                            "connections.html", user=user, data=data, returnUrl=f"/connections", pair_failed=True
                        )
                except Exception as e:
                    log.error(e)
                    return render_template(
                        "connections.html", user=user, data=data, returnUrl=f"/connections", pair_failed=True
                    )
            else:
                return render_template("errors/403.html"), 403

    @app.route("/connections/unpair")
    def user_profile_connections_unpair():
        with DBManager.create_session_scope() as db_session:
            if "user" not in session:
                return redirect(f"/login?n=/connections/")
            user = User.find_by_id(db_session, session["user"]["id"])
            if user is None:
                return render_template("no_user.html"), 404
            saved_data = db_session.query(UserConnections).filter_by(twitch_id=session["user"]["id"]).one_or_none()
            if not saved_data:
                return render_template("errors/403.html"), 403
            redis = RedisManager.get()
            unlinked_accounts = redis.get("unlinks-subs-discord")
            if unlinked_accounts is None:
                unlinked_accounts = {}
            else:
                unlinked_accounts = json.loads(unlinked_accounts)
            unlinked_accounts[saved_data.twitch_id] = saved_data.jsonify()
            unlinked_accounts = redis.set("unlinks-subs-discord", json.dumps(unlinked_accounts))
            saved_data._remove(db_session)
            db_session.commit()
            return redirect(f"/connections/")
