import datetime
import random
import string
import calendar
from sqlalchemy import Table
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from itsdangerous import URLSafeSerializer
from pajbot.managers import Base

# Todo: Move this to the config! IMPORTANT!
secret_key = "some-random-secret-damn-key"


class APIToken(Base):
    __tablename__ = 'tb_api_tokens'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('tb_user.id'))
    token = Column(String(255))
    salt = Column(String(32))

    # Define user relationship
    user = relationship("User", back_populates="tokens")

    scopes = []

    def __init__(self, user, scopes):
        self.id = None
        self.user_id = user.id
        self.salt = self.generate_random_salt()
        self.scopes = scopes

        s = URLSafeSerializer(secret_key, salt=self.salt)

        self.token = s.dumps({
            'issued_to': user.id,
            'issued_at': calendar.timegm(datetime.datetime.now().timetuple()),
            'scopes': scopes
        })

    @staticmethod
    def generate_random_salt(length=32):
        return ''.join([random.choice(string.ascii_letters + string.digits) for n in range(length)])

    def unlock_token(self, token=self.token):
        s = URLSafeSerializer(secret_key, salt=self.salt)
        return s.loads(token)
