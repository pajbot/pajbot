from flask import render_template
from sqlalchemy import func

from pajbot.models.db import DBManager
from pajbot.models.duel import UserDuelStats
from pajbot.models.user import User


def init(app):
    @app.route('/user/<username>')
    def user_profile(username):
        session = DBManager.create_session()
        user = session.query(User).filter_by(username=username).one_or_none()
        if user is None:
            return render_template('no_user.html'), 404

        rank = session.query(func.Count(User.id)).filter(User.points > user.points).one()
        rank = rank[0] + 1
        user.rank = rank

        user_duel_stats = session.query(UserDuelStats).filter_by(user_id=user.id).one_or_none()

        try:
            return render_template('user.html',
                    user=user,
                    user_duel_stats=user_duel_stats)
        finally:
            session.close()
