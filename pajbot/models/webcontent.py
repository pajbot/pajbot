from pajbot.managers.db import Base

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column


class WebContent(Base):
    __tablename__ = "web_content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page: Mapped[str]
    content: Mapped[str]
