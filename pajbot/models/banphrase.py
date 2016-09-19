import argparse
import logging

import sqlalchemy
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from pajbot.managers.db import Base
from pajbot.managers.db import DBManager
from pajbot.utils import find

log = logging.getLogger('pajbot')


class Banphrase(Base):
    __tablename__ = 'tb_banphrase'

    id = Column(Integer, primary_key=True)
    name = Column(String(256), nullable=False, default='')
    phrase = Column(String(256), nullable=False)
    length = Column(Integer, nullable=False, default=300)
    permanent = Column(Boolean, nullable=False, default=False)
    warning = Column(Boolean, nullable=False, default=True)
    notify = Column(Boolean, nullable=False, default=True)
    case_sensitive = Column(Boolean, nullable=False, default=False)
    enabled = Column(Boolean, nullable=False, default=True)
    sub_immunity = Column(Boolean,
            nullable=False,
            default=False,
            server_default=sqlalchemy.sql.expression.false())
    operator = Column(Enum('contains', 'startswith', 'endswith'),
            nullable=False,
            default='contains',
            server_default='contains')

    data = relationship('BanphraseData',
            uselist=False,
            cascade='',
            lazy='joined')

    DEFAULT_TIMEOUT_LENGTH = 300
    DEFAULT_NOTIFY = True

    def __init__(self, **options):
        self.id = None
        self.name = 'No name'
        self.length = self.DEFAULT_TIMEOUT_LENGTH
        self.permanent = False
        self.warning = True
        self.notify = self.DEFAULT_NOTIFY
        self.case_sensitive = False
        self.enabled = True
        self.operator = 'contains'

        self.set(**options)

    def set(self, **options):
        self.name = options.get('name', self.name)
        self.phrase = options.get('phrase', self.phrase)
        self.length = options.get('length', self.length)
        self.permanent = options.get('permanent', self.permanent)
        self.warning = options.get('warning', self.warning)
        self.notify = options.get('notify', self.notify)
        self.case_sensitive = options.get('case_sensitive', self.case_sensitive)
        self.sub_immunity = options.get('sub_immunity', self.sub_immunity)
        self.enabled = options.get('enabled', self.enabled)
        self.operator = options.get('operator', self.operator)

        self.refresh_operator()

    def refresh_operator(self):
        self.predicate = getattr(self, 'predicate_{}'.format(self.operator), None)

    def predicate_contains(self, message):
        if self.case_sensitive:
            return self.phrase in message
        else:
            return self.phrase.lower() in message.lower()

    def predicate_startswith(self, message):
        if self.case_sensitive:
            return message.startswith(self.phrase)
        else:
            return message.lower().startswith(self.phrase.lower())

    def predicate_endswith(self, message):
        if self.case_sensitive:
            return message.endswith(self.phrase)
        else:
            return message.lower().endswith(self.phrase.lower())

    def match(self, message, user):
        """
        Returns True if message matches our banphrase.
        Otherwise it returns False
        Respects case-sensitiveness option
        """
        if self.sub_immunity is True and user.subscriber is True:
            return False
        return self.predicate(message)

    def exact_match(self, message):
        """
        Returns True if message exactly matches our banphrase.
        Otherwise it returns False
        Respects case-sensitiveness option
        """
        if self.case_sensitive:
            return self.phrase == message
        else:
            return self.phrase.lower() == message.lower()


@sqlalchemy.event.listens_for(Banphrase, 'load')
def on_banphrase_load(target, context):
    target.refresh_operator()


@sqlalchemy.event.listens_for(Banphrase, 'refresh')
def on_banphrase_refresh(target, context, attrs):
    target.refresh_operator()


class BanphraseData(Base):
    __tablename__ = 'tb_banphrase_data'

    banphrase_id = Column(Integer,
            ForeignKey('tb_banphrase.id'),
            primary_key=True,
            autoincrement=False)
    num_uses = Column(Integer, nullable=False, default=0)
    added_by = Column(Integer, nullable=True)
    edited_by = Column(Integer, nullable=True)

    user = relationship('User',
            primaryjoin='User.id==BanphraseData.added_by',
            foreign_keys='User.id',
            uselist=False,
            cascade='',
            lazy='noload')

    user2 = relationship('User',
            primaryjoin='User.id==BanphraseData.edited_by',
            foreign_keys='User.id',
            uselist=False,
            cascade='',
            lazy='noload')

    def __init__(self, banphrase_id, **options):
        self.banphrase_id = banphrase_id
        self.num_uses = 0
        self.added_by = None
        self.edited_by = None

        self.set(**options)

    def set(self, **options):
        self.num_uses = options.get('num_uses', self.num_uses)
        self.added_by = options.get('added_by', self.added_by)
        self.edited_by = options.get('edited_by', self.edited_by)


class BanphraseManager:
    def __init__(self, bot):
        self.bot = bot
        self.banphrases = []
        self.enabled_banphrases = []
        self.db_session = DBManager.create_session(expire_on_commit=False)

        if self.bot:
            self.bot.socket_manager.add_handler('banphrase.update', self.on_banphrase_update)
            self.bot.socket_manager.add_handler('banphrase.remove', self.on_banphrase_remove)

    def on_banphrase_update(self, data, conn):
        try:
            banphrase_id = int(data['id'])
        except (KeyError, ValueError):
            log.warn('No banphrase ID found in on_banphrase_update')
            return False

        updated_banphrase = find(lambda banphrase: banphrase.id == banphrase_id, self.banphrases)
        if updated_banphrase:
            with DBManager.create_session_scope(expire_on_commit=False) as db_session:
                db_session.add(updated_banphrase)
                db_session.refresh(updated_banphrase)
                db_session.expunge(updated_banphrase)
        else:
            with DBManager.create_session_scope(expire_on_commit=False) as db_session:
                updated_banphrase = db_session.query(Banphrase).filter_by(id=banphrase_id).one_or_none()
                db_session.expunge_all()
                if updated_banphrase is not None:
                    self.db_session.add(updated_banphrase.data)

        if updated_banphrase:
            if updated_banphrase not in self.banphrases:
                self.banphrases.append(updated_banphrase)
            if updated_banphrase.enabled is True and updated_banphrase not in self.enabled_banphrases:
                self.enabled_banphrases.append(updated_banphrase)

        for banphrase in self.enabled_banphrases:
            if banphrase.enabled is False:
                self.enabled_banphrases.remove(banphrase)

    def on_banphrase_remove(self, data, conn):
        try:
            banphrase_id = int(data['id'])
        except (KeyError, ValueError):
            log.warn('No banphrase ID found in on_banphrase_remove')
            return False

        removed_banphrase = find(lambda banphrase: banphrase.id == banphrase_id, self.banphrases)
        if removed_banphrase:
            if removed_banphrase.data and removed_banphrase.data in self.db_session:
                self.db_session.expunge(removed_banphrase.data)

            if removed_banphrase in self.enabled_banphrases:
                self.enabled_banphrases.remove(removed_banphrase)

            if removed_banphrase in self.banphrases:
                self.banphrases.remove(removed_banphrase)

    def load(self):
        self.banphrases = self.db_session.query(Banphrase).all()
        for banphrase in self.banphrases:
            self.db_session.expunge(banphrase)
        self.enabled_banphrases = [banphrase for banphrase in self.banphrases if banphrase.enabled is True]
        return self

    def commit(self):
        self.db_session.commit()

    def create_banphrase(self, phrase, **options):
        for banphrase in self.banphrases:
            if banphrase.phrase == phrase:
                return banphrase, False

        banphrase = Banphrase(phrase=phrase, **options)
        banphrase.data = BanphraseData(banphrase.id, added_by=options.get('added_by', None))

        self.db_session.add(banphrase)
        self.db_session.add(banphrase.data)
        self.commit()
        self.db_session.expunge(banphrase)

        self.banphrases.append(banphrase)
        self.enabled_banphrases.append(banphrase)

        return banphrase, True

    def remove_banphrase(self, banphrase):
        self.banphrases.remove(banphrase)
        if banphrase in self.enabled_banphrases:
            self.enabled_banphrases.remove(banphrase)

        self.db_session.expunge(banphrase.data)
        self.db_session.delete(banphrase)
        self.db_session.delete(banphrase.data)
        self.commit()

    def punish(self, user, banphrase):
        """
        This method is responsible for calculating
        what sort of punishment a user deserves.

        The `permanent` flag takes precedence over the `warning` flag.
        This means if a banphrase is marked with the `permanent` flag,
        the user will be permanently banned even if this is his first strike.
        """

        if banphrase.data is not None:
            banphrase.data.num_uses += 1

        if banphrase.permanent is True:
            # Permanently ban user
            punishment = 'permanently banned'
            self.bot.ban(user.username)
        else:
            # Timeout user
            timeout_length, punishment = user.timeout(banphrase.length,
                    warning_module=self.bot.module_manager['warning'],
                    use_warnings=banphrase.warning)

            """ Finally, time out the user for whatever timeout length was required. """
            self.bot.timeout(user.username, timeout_length, reason='Banned phrase')

        if banphrase.notify is True and user.minutes_in_chat_online > 60:
            """ Last but not least, notify the user why he has been timed out
                if the banphrase wishes it. """
            notification_msg = 'You have been {punishment} because your message matched the "{banphrase.name}" banphrase.'.format(punishment=punishment, banphrase=banphrase)
            self.bot.whisper(user.username, notification_msg)

    def check_message(self, message, user):
        match = find(lambda banphrase: banphrase.match(message, user), self.enabled_banphrases)
        return match or False

    def find_match(self, message, id=None):
        match = None
        if id is not None:
            match = find(lambda banphrase: banphrase.id == id, self.banphrases)
        if match is None:
            match = find(lambda banphrase: banphrase.exact_match(message), self.banphrases)
        return match

    def parse_banphrase_arguments(self, message):
        parser = argparse.ArgumentParser()
        parser.add_argument('--length', dest='length', type=int)
        parser.add_argument('--time', dest='length', type=int)
        parser.add_argument('--duration', dest='length', type=int)
        parser.add_argument('--notify', dest='notify', action='store_true')
        parser.add_argument('--no-notify', dest='notify', action='store_false')
        parser.add_argument('--perma', dest='permanent', action='store_true')
        parser.add_argument('--no-perma', dest='permanent', action='store_false')
        parser.add_argument('--permanent', dest='permanent', action='store_true')
        parser.add_argument('--no-permanent', dest='permanent', action='store_false')
        parser.add_argument('--casesensitive', dest='case_sensitive', action='store_true')
        parser.add_argument('--no-casesensitive', dest='case_sensitive', action='store_false')
        parser.add_argument('--warning', dest='warning', action='store_true')
        parser.add_argument('--no-warning', dest='warning', action='store_false')
        parser.add_argument('--subimmunity', dest='sub_immunity', action='store_true')
        parser.add_argument('--no-subimmunity', dest='sub_immunity', action='store_false')
        parser.add_argument('--name', nargs='+', dest='name')
        parser.set_defaults(length=None,
                notify=None,
                permanent=None,
                case_sensitive=None,
                warning=None,
                sub_immunity=None)

        try:
            args, unknown = parser.parse_known_args(message.split())
        except SystemExit:
            return False, False
        except:
            log.exception('Unhandled exception in add_command')
            return False, False

        # Strip options of any values that are set as None
        options = {k: v for k, v in vars(args).items() if v is not None}
        response = ' '.join(unknown)

        if 'name' in options:
            options['name'] = ' '.join(options['name'])

        log.info(options)

        return options, response
