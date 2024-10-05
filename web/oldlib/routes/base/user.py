from pajbot.managers.db import DBManager
from pajbot.models.roulette import Roulette
from pajbot.models.user import User

from flask import render_template


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

            return render_template("user.html", user=user, roulette_stats=roulette_stats, roulettes=roulettes)
