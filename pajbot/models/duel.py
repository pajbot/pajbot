import datetime
import logging

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship

from pajbot.managers import Base

log = logging.getLogger('pajbot')


class UserDuelStats(Base):
    __tablename__ = 'tb_user_duel_stats'

    user_id = Column(Integer, ForeignKey('tb_user.id'), primary_key=True, autoincrement=False)
    duels_won = Column(Integer, nullable=False, default=0)
    duels_total = Column(Integer, nullable=False, default=0)
    points_won = Column(Integer, nullable=False, default=0)
    points_lost = Column(Integer, nullable=False, default=0)
    last_duel = Column(DateTime, nullable=True)
    current_streak = Column(Integer, nullable=False, default=0)
    longest_winstreak = Column(Integer, nullable=False, default=0)
    longest_losestreak = Column(Integer, nullable=False, default=0)

    user = relationship('User',
            cascade='',
            uselist=False,
            backref=backref('duel_stats',
                uselist=False,
                cascade='',
                lazy='select'))

    def __init__(self, user_id):
        self.user_id = user_id
        self.duels_won = 0
        self.duels_total = 0
        self.points_won = 0
        self.points_lost = 0
        self.current_streak = 0
        self.longest_winstreak = 0
        self.longest_losestreak = 0

    @hybrid_property
    def duels_lost(self):
        return self.duels_total - self.duels_won

    @hybrid_property
    def winrate(self):
        return self.duels_won * 100 / self.duels_total

    @hybrid_property
    def profit(self):
        return self.points_won - self.points_lost


class DuelManager:
    def __init__(self, bot):
        self.db_session = bot.users.db_session

    def get_user_duel_stats(self, user):
        if user.duel_stats is None:
            user.duel_stats = UserDuelStats(user.id)
            self.db_session.add(user.duel_stats)
        return user.duel_stats

    def user_won(self, user, points_won):
        """
        Arguments:
        user = a User object for the person who won the duel
        points_won = an Integer for how many points the user just won
        """

        user_duel_stats = self.get_user_duel_stats(user)
        user_duel_stats.duels_won += 1
        user_duel_stats.duels_total += 1
        user_duel_stats.points_won += points_won
        user_duel_stats.last_duel = datetime.datetime.now()

        if user_duel_stats.current_streak > 0:
            user_duel_stats.current_streak += 1
        else:
            user_duel_stats.current_streak = 1
        if user_duel_stats.current_streak > user_duel_stats.longest_winstreak:
            user_duel_stats.longest_winstreak = user_duel_stats.current_streak

        return user_duel_stats

    def user_lost(self, user, points_lost):
        """
        Arguments:
        user = a User object for the person who lost the duel
        points_lost = an Integer for how many points the user just lost
        """

        user_duel_stats = self.get_user_duel_stats(user)
        user_duel_stats.duels_total += 1
        user_duel_stats.points_lost += points_lost
        user_duel_stats.last_duel = datetime.datetime.now()

        if user_duel_stats.current_streak < 0:
            user_duel_stats.current_streak -= 1
        else:
            user_duel_stats.current_streak = -1
        if abs(user_duel_stats.current_streak) > user_duel_stats.longest_losestreak:
            user_duel_stats.longest_losestreak = user_duel_stats.current_streak

        return user_duel_stats
