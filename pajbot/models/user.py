import logging
from contextlib import contextmanager

from datetime import timedelta
from sqlalchemy import BOOLEAN, INT, TEXT, BIGINT, Interval, or_, and_
from sqlalchemy.sql.functions import func
from sqlalchemy import Column
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, foreign
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.sql import functions
from sqlalchemy_utc import UtcDateTime

from pajbot import utils
from pajbot.exc import FailedCommand
from pajbot.managers.db import Base
from pajbot.managers.redis import RedisManager
from pajbot.models.duel import UserDuelStats

log = logging.getLogger(__name__)


class UserRank(Base):
    __tablename__ = "user_rank"

    user_id = Column(TEXT, primary_key=True, nullable=False)
    points_rank = Column(BIGINT, nullable=False)
    num_lines_rank = Column(BIGINT, nullable=False)


class UserBasics:
    def __init__(self, id, login, name):
        self.id = id
        self.login = login
        self.name = name

    def jsonify(self):
        return {"id": self.id, "login": self.login, "name": self.name}


class User(Base):
    __tablename__ = "user"

    # Twitch user ID
    id = Column(TEXT, primary_key=True, nullable=False)

    # Twitch user login name
    _login = Column("login", TEXT, nullable=False, index=True)

    # login_last_updated describes when this user's login name was last authoritatively updated,
    # for example through an API response from Twitch,
    # or a chat message from this user's ID, a login to the web interface, etc.
    # Since we do not enforce the login to be unique, there can be two users with the same username
    # (e.g. user with old name deletes account, and new account appears with the same username
    # through Twitch name recycling)
    # This value helps us decide which user to pick when selecting by login - we will pick the
    # user with the most recent login_last_updated.
    # See User.find_by_login and similar functions for queries that use this value.
    # This value is updated via a database trigger (created in 0004_unify_user_model.py)
    # that sets this value to NOW() on every update to `login`.
    # This value is also initialized to NOW() on every new row.
    # To make sure SQLAlchemy always issues a UPDATE for the login even if the login didn't really change,
    # (the value didn't change), a @property and @setter exist below (named `login`), that mark
    # the login property as "modified" even if the value has not changed.
    #
    # So for example, this code will implicitly set login_last_updated on commit:
    # e.g. we received a chat message from Snusbot (id=62541963, login=snusbot, display_name=Snusbot):
    # with DBManager.create_session_scope() as db_session:
    #     user = db_session.query(User).filter_by(id='62541963').one()
    #     user.login = 'snusbot'
    #     user.name = 'Snusbot'
    # This would issue an `UPDATE` command that sets user.login even if the login was already "snusbot" before,
    # and so the login_last_updated becomes updated on the database side via the trigger.
    login_last_updated = Column(UtcDateTime(), nullable=False, server_default="NOW()")

    # Twitch user display name
    name = Column(TEXT, nullable=False, index=True)

    level = Column(INT, nullable=False, server_default="100")
    points = Column(BIGINT, nullable=False, server_default="0", index=True)
    subscriber = Column(BOOLEAN, nullable=False, server_default="FALSE")
    moderator = Column(BOOLEAN, nullable=False, server_default="FALSE")
    time_in_chat_online = Column(Interval, nullable=False, server_default="INTERVAL '0 minutes'")
    time_in_chat_offline = Column(Interval, nullable=False, server_default="INTERVAL '0 minutes'")
    num_lines = Column(BIGINT, nullable=False, server_default="0", index=True)
    tokens = Column(INT, nullable=False, server_default="0")
    last_seen = Column(UtcDateTime(), nullable=True, server_default="NULL")
    last_active = Column(UtcDateTime(), nullable=True, server_default="NULL")
    ignored = Column(BOOLEAN, nullable=False, server_default="FALSE")
    banned = Column(BOOLEAN, nullable=False, server_default="FALSE")
    timeout_end = Column(UtcDateTime(), nullable=True, server_default="NULL")
    vip = Column(BOOLEAN, nullable=False, server_default="FALSE")
    founder = Column(BOOLEAN, nullable=False, server_default="FALSE")

    _rank = relationship("UserRank", primaryjoin=foreign(id) == UserRank.user_id, lazy="select")

    def __init__(self, *args, **kwargs):
        self.level = 100
        self.points = 0
        self.subscriber = False
        self.moderator = False
        self.time_in_chat_online = timedelta(minutes=0)
        self.time_in_chat_offline = timedelta(minutes=0)
        self.num_lines = 0
        self.tokens = 0
        self.last_seen = None
        self.last_active = None
        self.ignored = False
        self.banned = False
        self.timeout_end = None
        self.vip = False
        self.founder = False

        super().__init__(*args, **kwargs)

    _duel_stats = relationship(
        UserDuelStats, uselist=False, cascade="all, delete-orphan", passive_deletes=True, back_populates="user"
    )

    @hybrid_property
    def username(self):
        # retained for backwards compatibility with commands that still use $(source:username) (and similar)
        return self.login

    @hybrid_property
    def username_raw(self):
        # retained for backwards compatibility with commands that still use $(source:username_raw) (and similar)
        return self.name

    @hybrid_property
    def login(self):
        return self._login

    @login.setter
    def login(self, new_login):
        self._login = new_login
        # force SQLAlchemy to update the value in the database even if the value did not change
        # see above comment for details on why this is implemented this way
        flag_modified(self, "_login")

    @property
    def points_rank(self):
        if self._rank:
            return self._rank.points_rank
        else:
            # user is relatively new, and they are not inside the user_rank materialized view yet.
            # on next refresh, they will be included.
            return 420

    @property
    def num_lines_rank(self):
        if self._rank:
            return self._rank.num_lines_rank
        else:
            # user is relatively new, and they are not inside the user_rank materialized view yet.
            # on next refresh, they will be included.
            return 1337

    @property
    def minutes_in_chat_online(self):
        # retained for backwards compatibility with commands that still use this property
        return int(self.time_in_chat_online.total_seconds() / 60)

    @property
    def minutes_in_chat_offline(self):
        # retained for backwards compatibility with commands that still use this property
        return int(self.time_in_chat_offline.total_seconds() / 60)

    @hybrid_property
    def timed_out(self):
        return self.timeout_end is not None and self.timeout_end > utils.now()

    @timed_out.expression
    def timed_out(self):
        return and_(self.timeout_end.isnot(None), self.timeout_end > functions.now())

    @timed_out.setter
    def timed_out(self, timed_out):
        # You can do user.timed_out = False to set user.timeout_end = None
        if timed_out is not False:
            raise ValueError("Only `False` may be assigned to User.timed_out")
        self.timeout_end = None

    @property
    def duel_stats(self):
        if self._duel_stats is None:
            self._duel_stats = UserDuelStats()
        return self._duel_stats

    def can_afford(self, points_to_spend):
        return self.points >= points_to_spend

    def can_afford_with_tokens(self, cost):
        return self.tokens >= cost

    @contextmanager
    def spend_currency_context(self, points, tokens):
        try:
            with self._spend_currency_context(points, "points"), self._spend_currency_context(tokens, "tokens"):
                yield
        except FailedCommand:
            pass

    @contextmanager
    def _spend_currency_context(self, amount, currency):
        # self.{points,tokens} -= spend_amount
        setattr(self, currency, getattr(self, currency) - amount)

        try:
            yield
        except:
            log.debug(f"Returning {amount} {currency} to {self}")
            setattr(self, currency, getattr(self, currency) + amount)
            raise

    def get_warning_keys(self, total_chances, prefix):
        """Returns a list of keys that are used to store the users warning status in redis.
        Example: ['warnings:some-prefix:11148817:0', 'warnings:some-prefix:11148817:1']"""
        return [f"warnings:{prefix}:{self.id}:{warning_id}" for warning_id in range(0, total_chances)]

    @staticmethod
    def get_warnings(redis, warning_keys):
        """Pass through a list of warning keys.
        Example of warning_keys syntax: ['warnings:some-prefix:11148817:0', 'warnings:some-prefix:11148817:1']
        Returns a list of values for the warning keys list above.
        Example: [b'1', None]
        Each instance of None in the list means one more Chance
        before a full timeout is in order."""

        return redis.mget(warning_keys)

    @staticmethod
    def get_chances_used(warnings):
        """Returns a number between 0 and n where n is the amount of
        chances a user has before he should face the full timeout length."""

        return len(warnings) - warnings.count(None)

    @staticmethod
    def add_warning(redis, timeout, warning_keys, warnings):
        """Returns a number between 0 and n where n is the amount of
        chances a user has before he should face the full timeout length."""

        for i in range(0, len(warning_keys)):
            if warnings[i] is None:
                redis.setex(warning_keys[i], time=timeout, value=1)
                return True

        return False

    def timeout(self, timeout_length, warning_module=None, use_warnings=True):
        """Returns a tuple with the follow data:
        How long to timeout the user for, and what the punishment string is
        set to.
        The punishment string is used to clarify whether this was a warning or the real deal.
        """

        punishment = f"timed out for {timeout_length} seconds"

        if use_warnings and warning_module is not None:
            redis = RedisManager.get()

            # How many chances the user has before receiving a full timeout.
            total_chances = warning_module.settings["total_chances"]

            warning_keys = self.get_warning_keys(total_chances, warning_module.settings["redis_prefix"])
            warnings = self.get_warnings(redis, warning_keys)

            chances_used = self.get_chances_used(warnings)

            if chances_used < total_chances:
                """The user used up one of his warnings.
                Calculate for how long we should time him out."""
                timeout_length = warning_module.settings["base_timeout"] * (chances_used + 1)
                punishment = f"timed out for {timeout_length} seconds (warning)"

                self.add_warning(redis, warning_module.settings["length"], warning_keys, warnings)

        return (timeout_length, punishment)

    def jsonify(self):
        return {
            "id": self.id,
            "login": self.login,
            "name": self.name,
            "level": self.level,
            "points": self.points,
            "points_rank": self.points_rank,
            "subscriber": self.subscriber,
            "moderator": self.moderator,
            "time_in_chat_online": self.time_in_chat_online.total_seconds(),
            "time_in_chat_offline": self.time_in_chat_offline.total_seconds(),
            "num_lines": self.num_lines,
            "num_lines_rank": self.num_lines_rank,
            "tokens": self.tokens,
            "last_seen": self.last_seen.isoformat() if self.last_seen is not None else None,
            "last_active": self.last_active.isoformat() if self.last_active is not None else None,
            "ignored": self.ignored,
            "banned": self.banned,
            "timeout_end": self.timeout_end.isoformat() if self.timeout_end is not None else None,
            "vip": self.vip,
            "founder": self.founder,
        }

    def __eq__(self, other):
        if not isinstance(other, User):
            return False
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        # this is here so we can use the user object directly in string substitutions
        # e.g. bot.say(f"{user}, successfully done something!")
        # would substitute the user's display name in the place of {user}.
        return self.name

    @staticmethod
    def _create(db_session, id, login, name):
        user = User(id=id, login=login, name=name)
        db_session.add(user)
        return user

    @staticmethod
    def from_basics(db_session, basics):
        user_from_db = db_session.query(User).filter_by(id=basics.id).one_or_none()
        if user_from_db is not None:
            # Update the existing user with the new data
            user_from_db.login = basics.login
            user_from_db.name = basics.name
            return user_from_db

        # no user in DB! Create new user and add to SQLAlchemy session.
        return User._create(db_session, basics.id, basics.login, basics.name)

    @staticmethod
    def find_or_create_from_login(db_session, twitch_helix_api, login):
        user_from_db = (
            db_session.query(User).filter_by(login=login).order_by(User.login_last_updated.desc()).one_or_none()
        )
        if user_from_db is not None:
            return user_from_db

        # no user in DB! Query Helix API for user basics, then create user/update existing user and return.
        basics = twitch_helix_api.get_user_basics_by_login(login)
        if basics is None:
            return None

        return User.from_basics(db_session, basics)

    @staticmethod
    def find_or_create_from_user_input(db_session, twitch_helix_api, input, always_fresh=False):
        input = User._normalize_user_username_input(input)

        if not always_fresh:
            user_from_db = (
                db_session.query(User)
                .filter(or_(User.login == input, User.name == input))
                .order_by(User.login_last_updated.desc())
                .limit(1)
                .one_or_none()
            )

            if user_from_db is not None:
                return user_from_db

        basics = twitch_helix_api.get_user_basics_by_login(input)
        if basics is None:
            return None

        return User.from_basics(db_session, basics)

    @staticmethod
    def _normalize_user_username_input(input):
        # Remove some characters commonly present when people autocomplete names, e.g.
        #  - @Pajlada
        #  - pajlada,
        #  - @pajlada,
        # and similar
        return input.lower().strip().lstrip("@").rstrip(",")

    @staticmethod
    def find_by_user_input(db_session, input):
        input = User._normalize_user_username_input(input)

        # look for a match in both the login and name
        return (
            db_session.query(User)
            .filter(or_(User.login == input, func.lower(User.name) == input))
            .order_by(User.login_last_updated.desc())
            .limit(1)
            .one_or_none()
        )

    @staticmethod
    def find_by_login(db_session, login):
        return (
            db_session.query(User)
            .filter_by(login=login)
            .order_by(User.login_last_updated.desc())
            .limit(1)
            .one_or_none()
        )

    @staticmethod
    def find_by_id(db_session, id):
        return db_session.query(User).filter_by(id=id).one_or_none()


class UserChannelInformation:
    """UserChannelInformation represents part of the information fetched
    from the Helix Get Channel Information endpoint https://dev.twitch.tv/docs/api/reference#get-channel-information"""

    def __init__(self, broadcaster_language, game_id, game_name, title):
        self.broadcaster_language = broadcaster_language
        self.game_id = game_id
        self.game_name = game_name
        self.title = title

    def jsonify(self):
        return {
            "broadcaster_language": self.broadcaster_language,
            "game_id": self.game_id,
            "game_name": self.game_name,
            "title": self.title,
        }

    @staticmethod
    def from_json(json_data):
        return UserChannelInformation(
            broadcaster_language=json_data["broadcaster_language"],
            game_id=json_data["game_id"],
            game_name=json_data["game_name"],
            title=json_data["title"],
        )
