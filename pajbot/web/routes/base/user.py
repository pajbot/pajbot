from flask import render_template
from sqlalchemy import func

from pajbot.managers import DBManager
from pajbot.models.duel import UserDuelStats
from pajbot.models.roulette import Roulette
from pajbot.models.user import User


def init(app):
    @app.route('/user/<username>')
    def user_profile(username):
        with DBManager.create_session_scope() as db_session:
            user = db_session.query(User).filter_by(username=username).one_or_none()
            if user is None:
                return render_template('no_user.html'), 404

            rank = db_session.query(func.Count(User.id)).filter(User.points > user.points).one()
            rank = rank[0] + 1
            user.rank = rank

            user_duel_stats = db_session.query(UserDuelStats).filter_by(user_id=user.id).one_or_none()

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

                roulette_stats = {
                        'profit': profit,
                        'total_points': total_points,
                        'biggest_win': biggest_win,
                        'biggest_loss': biggest_loss,
                        'num_roulettes': num_roulettes,
                        'biggest_winstreak': biggest_winstreak,
                        'biggest_losestreak': biggest_losestreak,
                        'winrate': winrate,
                        'winrate_str': '{:.2f}%'.format(winrate * 100),
                        'roulette_base_winrate': 1.0 - app.module_manager['roulette'].settings['rigged_percentage'] / 100,
                        }

            return render_template('user.html',
                    user=user,
                    user_duel_stats=user_duel_stats,
                    roulette_stats=roulette_stats,
                    roulettes=roulettes)
