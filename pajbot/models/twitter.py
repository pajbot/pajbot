"""
Follow user through !twitterfollow command in chat
Unfollow user through !twitterunfollow command in chat
Follow user through admin web UI
Unfollow user through admin web UI
"""
from typing import Any, Dict, Optional

from pajbot.managers.db import Base

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column


class TwitterUser(Base):
    __tablename__ = "twitter_following"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # TODO: Make a DB migration to make username not null
    username: Mapped[Optional[str]]

    def __init__(self, username: str) -> None:
        self.username = username

    def jsonify(self) -> Dict[str, Any]:
        return {"id": self.id, "username": self.username}
