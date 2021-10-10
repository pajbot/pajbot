from typing import Any, Dict

from pajbot.managers.db import Base

from sqlalchemy import INT, TEXT, Column


class TwitterUser(Base):
    __tablename__ = "twitter_following"

    id = Column(INT, primary_key=True)
    username = Column(TEXT)  # NOTE: This should *not* be nullable. A DB migration will be necessary for this change

    def __init__(self, username: str) -> None:
        self.username = username

    def jsonify(self) -> Dict[str, Any]:
        return {"id": self.id, "username": self.username}
