from typing import Any

from pajbot.managers.db import Base

from sqlalchemy import INT, TEXT, Column


class TwitterUser(Base):
    __tablename__ = "twitter_following"

    id = Column(INT, primary_key=True)
    username = Column(TEXT)

    def __init__(self, username: str) -> None:
        self.username = username

    def jsonify(self) -> dict[str, Any]:
        return {"id": self.id, "username": self.username}
