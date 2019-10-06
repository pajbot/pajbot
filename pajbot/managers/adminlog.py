import logging

from sqlalchemy import Column, INT, TEXT, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy_utc import UtcDateTime

from pajbot import utils
from pajbot.managers.db import Base, DBManager

log = logging.getLogger(__name__)


class LogEntryTemplate:
    def __init__(self, message_fmt):
        self.message_fmt = message_fmt

    def get_message(self, *args):
        return self.message_fmt.format(*args)


class AdminLogEntry(Base):
    __tablename__ = "admin_log_entry"

    id = Column(INT, primary_key=True)
    type = Column(TEXT, nullable=False)
    user_id = Column(TEXT, ForeignKey("user.id", ondelete="SET NULL"))
    message = Column(TEXT, nullable=False)
    created_at = Column(UtcDateTime(), nullable=False, index=True)
    data = Column(JSONB, nullable=False)

    user = relationship("User")


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
    def add_entry(entry_type, source, message, data={}):
        with DBManager.create_session_scope() as db_session:
            entry_object = AdminLogEntry(
                type=entry_type, user_id=source.id, message=message, created_at=utils.now(), data=data
            )
            db_session.add(entry_object)

    @staticmethod
    def post(entry_type, source, *args, data={}):
        message = AdminLogManager.TEMPLATES[entry_type].get_message(*args)
        AdminLogManager.add_entry(entry_type, source, message, data=data)
