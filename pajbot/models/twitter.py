from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String

from pajbot.managers import Base


class TwitterUser(Base):
    __tablename__ = 'tb_twitter_following'

    id = Column(Integer, primary_key=True)
    username = Column(String(32))

    def __init__(self, username):
        self.username = username
