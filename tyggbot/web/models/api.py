from tyggbot.models.user import User
from tyggbot.models.db import DBManager

from flask import Blueprint
from flask import jsonify
from flask import make_response
from sqlalchemy import func


page = Blueprint('api', __name__)

sqlconn = False


@page.route('/api/v1/user/<username>')
def get_user(username):
    session = DBManager.create_session()
    user = session.query(User).filter_by(username=username).one_or_none()
    if user is None:
        return make_response(jsonify({'error': 'Not found'}), 404)

    rank = session.query(func.Count(User.id)).filter(User.points > user.points).one()
    rank = rank[0] + 1
    session.close()
    if user:
        accessible_data = {
                'id': user.id,
                'username': user.username,
                'username_raw': user.username_raw,
                'points': user.points,
                'rank': rank,
                'level': user.level,
                'last_seen': user.last_seen,
                'last_active': user.last_active,
                'subscriber': user.subscriber,
                'num_lines': user.num_lines,
                'minutes_in_chat_online': user.minutes_in_chat_online,
                'minutes_in_chat_offline': user.minutes_in_chat_offline,
                'banned': user.banned,
                'ignored': user.ignored,
                }
        return jsonify(accessible_data)

    return make_response(jsonify({'error': 'Not found'}), 404)
