import logging

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer

from pajbot import utils
from pajbot.managers.db import Base

log = logging.getLogger(__name__)


class Roulette(Base):
    __tablename__ = "tb_roulette"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True, nullable=False)
    created_at = Column(DateTime, nullable=False)
    points = Column(Integer, nullable=False)

    def __init__(self, user_id, points):
        self.user_id = user_id
        self.created_at = utils.now()
        self.points = points
