import logging
import datetime

from tyggbot.models.user import User
from tyggbot.models.db import DBManager, Base

from sqlalchemy import Column, Integer, DateTime

log = logging.getLogger('tyggbot')


class UserDuelStats(Base):
    __tablename__ = 'tb_user_duel_stats'

    user_id = Column(Integer, primary_key=True, autoincrement=False)
    duels_won = Column(Integer, nullable=False, default=0)
    duels_total = Column(Integer, nullable=False, default=0)
    points_won = Column(Integer, nullable=False, default=0)
    points_lost = Column(Integer, nullable=False, default=0)
    last_duel = Column(DateTime, nullable=True)

    def __init__(self, user_id):
        self.user_id = user_id
        self.duels_won = 0
        self.duels_total = 0
        self.points_won = 0
        self.points_lost = 0

class DuelManager:
    db_session = None

    def init_session(self):
        """
        Initializes the DB Session if required.
        """

        if self.db_session is None:
            self.db_session = DBManager.create_session()

    def commit(self):
        """
        Commits any changed to the db session if the session is active
        """

        if self.db_session is not None:
            self.db_session.commit()
            self.db_session.close()
            self.db_session = None

    def get_user_duel_stats(self, user_id):
        self.init_session()
        user_duel_stats = self.db_session.query(UserDuelStats).filter_by(user_id=user_id).first()
        if user_duel_stats is None:
            user_duel_stats = UserDuelStats(user_id)
            self.db_session.add(user_duel_stats)
        return user_duel_stats

    def user_won(self, user, points_won):
        """
        Arguments:
        user = a User object for the person who won the duel
        points_won = an Integer for how many points the user just won
        """

        user_duel_stats = self.get_user_duel_stats(user.id)
        user_duel_stats.duels_won += 1
        user_duel_stats.duels_total += 1
        user_duel_stats.points_won += points_won
        user_duel_stats.last_duel = datetime.datetime.now()

    def user_lost(self, user, points_lost):
        """
        Arguments:
        user = a User object for the person who lost the duel
        points_lost = an Integer for how many points the user just lost
        """

        user_duel_stats = self.get_user_duel_stats(user.id)
        user_duel_stats.duels_total += 1
        user_duel_stats.points_lost += points_lost
        user_duel_stats.last_duel = datetime.datetime.now()
