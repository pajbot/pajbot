from sqlalchemy import Column, INT, TEXT

from pajbot.managers.db import Base


class TwitterUser(Base):
    __tablename__ = "twitter_following"

    id = Column(INT, primary_key=True)
    username = Column(TEXT)

    def __init__(self, username):
        self.username = username

    def jsonify(self):
        return {"id": self.id, "username": self.username}
