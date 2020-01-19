import logging

from sqlalchemy import TEXT, INT
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from pajbot.managers.db import Base

log = logging.getLogger(__name__)


class UserConnections(Base):
    __tablename__ = "user_connections"

    # Twitch user ID
    twitch_id = Column(INT, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, autoincrement=False)
    twitch_login = Column(TEXT, nullable=False)
    twitch_user = relationship("User")

    # Discord user id
    discord_user_id = Column(TEXT, nullable=False)
    discord_username = Column(TEXT, nullable=False)
    discord_tier = Column(INT, nullable=True)

    # steamID64
    steam_id = Column(TEXT, nullable=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def jsonify(self):
        return {
            "twitch_id": self.twitch_id,
            "twitch_login": self.twitch_login,
            "discord_tier": self.tier,
            "discord_user_id": self.discord_user_id,
            "discord_username": self.discord_username,
            "steam_id": self.steam_id,
        }

    def __eq__(self, other):
        if not isinstance(other, UserConnections):
            return False
        return self.twitch_id == other.twitch_id

    def _remove(self, db_session):
        db_session.delete(self)

    def _update_discord_username(self, db_session, discord_username):
        self.discord_username = discord_username
        db_session.merge(self)
        return self

    def _update_twitch_login(self, db_session, twitch_login):
        self.twitch_login = twitch_login
        db_session.merge(self)
        return self

    def _update_tier(self, db_session, tier):
        self.discord_tier = tier
        db_session.merge(self)
        return self

    @hybrid_property
    def tier(self):
        return self.discord_tier if self.discord_tier else 0

    @staticmethod
    def _create(db_session, twitch_id, twitch_login, discord_user_id, discord_username, steam_id, discord_tier=None):
        user_con = UserConnections(
            twitch_id=twitch_id,
            twitch_login=twitch_login,
            discord_tier=discord_tier,
            discord_user_id=discord_user_id,
            discord_username=discord_username,
            steam_id=steam_id,
        )
        db_session.add(user_con)
        return user_con

    @staticmethod
    def _from_discord_id(db_session, discord_user_id):
        return db_session.query(UserConnections).filter_by(discord_user_id=discord_user_id).one_or_none()

    @staticmethod
    def _from_twitch_id(db_session, twitch_id):
        return db_session.query(UserConnections).filter_by(twitch_id=twitch_id).one_or_none()

    @staticmethod
    def _by_tier(db_session, tier):
        return db_session.query(UserConnections).filter_by(discord_tier=tier).all()
