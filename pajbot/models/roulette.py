import logging

from sqlalchemy import Column, INT
from sqlalchemy_utc import UtcDateTime

from pajbot import utils
from pajbot.managers.db import Base

log = logging.getLogger(__name__)


class Roulette(Base):
    __tablename__ = "roulette"

    id = Column(INT, primary_key=True)
    user_id = Column(INT, index=True, nullable=False)
    created_at = Column(UtcDateTime(), nullable=False)
    points = Column(INT, nullable=False)

    def __init__(self, user_id, points):
        self.user_id = user_id
        self.created_at = utils.now()
        self.points = points
