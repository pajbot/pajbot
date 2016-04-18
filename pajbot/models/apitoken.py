import calendar
import datetime
import random
import string

from itsdangerous import URLSafeSerializer

from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String

from sqlalchemy.orm import reconstructor
from sqlalchemy.orm import relationship

from pajbot.managers import Base
from pajbot.managers import DBManager

# Initialized in app.py
secret_key = None


class APIToken(Base):
    __tablename__ = 'tb_api_token'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('tb_user.id'))
    token = Column(String(255))
    salt = Column(String(32))

    # Define user relationship
    user = relationship('User', back_populates='tokens')

    scopes = []
    decoded = {}

    def __init__(self, user, scopes):
        self.id = None
        self.user_id = user.id
        self.salt = self.__generate_random_salt()
        self.scopes = scopes

        s = URLSafeSerializer(secret_key, salt=self.salt)

        self.decoded = {
            'issued_to': user.id,
            'issued_at': calendar.timegm(datetime.datetime.now().timetuple()),
            'scopes': scopes
        }
        self.token = s.dumps(self.decoded)

    @reconstructor
    def init_on_load(self):
        self.decoded = self.unlock_token(self.token)
        self.scopes = self.decoded.get('scopes', [])

    def __generate_random_salt(self, length=32):
        return ''.join([random.choice(string.ascii_letters + string.digits) for n in range(length)])

    def has_scope(self, scope):
        if scope == '':
            return False

        return scope in self.scopes

    def unlock_token(self, token):
        s = URLSafeSerializer(secret_key, salt=self.salt)
        sig_okay, payload = s.loads_unsafe(token)
        if not sig_okay:
            raise InvalidToken(token)
        return payload

    def serialize(self):
        return self.decoded


class InvalidToken(Exception):
    def __init__(self, token):
        self.token = token

    def __str__(self):
        return 'Invalid token provided.'


class APITokenManager:
    def find(self, token):
        if token == '':
            raise InvalidToken(token)

        with DBManager.create_session_scope(expire_on_commit=False) as db_session:
            api_token = db_session.query(APIToken).filter_by(token=token).one_or_none()

            if not api_token:
                raise InvalidToken(token)

            return api_token

    def generate_token_for_user(self, user, scopes):
        if not user:
            return None

        token = APIToken(user, scopes)
        DBManager.session_add_expunge(token)

        return token

    def generate_token_for_username(self, username, scopes):
        from pajbot.models.user import UserManager
        user_manager = UserManager()
        user = user_manager.find(username)

        if not user:
            return None

        return self.generate_token_for_user(user, scopes)
