from typing import Any, Dict, Optional

from pajbot.managers.db import Base

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column


class TwitterUser(Base):
    __tablename__ = "twitter_following"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[Optional[str]]

    def __init__(self, username: str) -> None:
        self.username = username

    def jsonify(self) -> Dict[str, Any]:
        return {"id": self.id, "username": self.username}
