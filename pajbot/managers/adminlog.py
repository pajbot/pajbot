"""
Admin logs are created with post and add_entry

Admin logs are read & rendered by admin's home.{py.html}
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

import datetime
import logging

from pajbot import utils
from pajbot.managers.db import Base, DBManager

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_utc import UtcDateTime

if TYPE_CHECKING:
    from pajbot.models.user import User

log = logging.getLogger(__name__)


class LogEntryTemplate:
    def __init__(self, message_fmt: str) -> None:
        self.message_fmt = message_fmt

    def get_message(self, *args) -> str:
        return self.message_fmt.format(*args)


class AdminLogEntry(Base):
    __tablename__ = "admin_log_entry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str]
    user_id: Mapped[Optional[str]] = mapped_column(Text, ForeignKey("user.id", ondelete="SET NULL"))
    message: Mapped[str]
    created_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime(), index=True)
    data: Mapped[Any] = mapped_column(JSONB, nullable=False)

    user: Mapped[Optional[User]] = relationship("User")


class AdminLogManager:
    TEMPLATES = {
        "Banphrase added": LogEntryTemplate('Added banphrase #{} "{}"'),
        "Banphrase edited": LogEntryTemplate('Edited banphrase #{} from "{}"'),
        "Banphrase removed": LogEntryTemplate('Removed banphrase #{} "{}"'),
        "Banphrase toggled": LogEntryTemplate('{} banphrase #{} "{}"'),
        "Blacklist link added": LogEntryTemplate('Added blacklist link "{}"'),
        "Blacklist link removed": LogEntryTemplate('Removed blacklisted link "{}"'),
        "Module edited": LogEntryTemplate('Edited module "{}"'),
        "Module toggled": LogEntryTemplate('{} module "{}"'),
        "Timer added": LogEntryTemplate('Added timer "{}"'),
        "Timer removed": LogEntryTemplate('Removed timer "{}"'),
        "Timer toggled": LogEntryTemplate('{} timer "{}"'),
        "Whitelist link added": LogEntryTemplate('Added whitelist link "{}"'),
        "Whitelist link removed": LogEntryTemplate('Removed whitelisted link "{}"'),
    }

    @staticmethod
    def add_entry(entry_type: str, source: User, message: str, data={}) -> None:
        with DBManager.create_session_scope() as db_session:
            entry_object = AdminLogEntry(
                type=entry_type, user_id=source.id, message=message, created_at=utils.now(), data=data
            )
            db_session.add(entry_object)

    @staticmethod
    def post(entry_type: str, source: User, *args, data={}) -> None:
        message = AdminLogManager.TEMPLATES[entry_type].get_message(*args)
        AdminLogManager.add_entry(entry_type, source, message, data=data)
