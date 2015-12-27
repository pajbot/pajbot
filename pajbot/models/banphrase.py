import json
import time
import logging
from collections import UserDict
import argparse
import datetime
import re

from pajbot.tbutil import find
from pajbot.models.db import DBManager, Base
from pajbot.models.action import ActionParser, RawFuncAction, FuncAction
from pajbot.managers.redis import RedisManager

from sqlalchemy import orm
from sqlalchemy.orm import relationship, joinedload
from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.mysql import TEXT

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

        self.set(**options)

    def set(self, **options):
        self.name = options.get('name', self.name)
        self.phrase = options.get('phrase', self.phrase)
        self.length = options.get('length', self.length)
        self.permanent = options.get('permanent', self.permanent)
        self.warning = options.get('warning', self.warning)
        self.notify = options.get('notify', self.notify)
        self.case_sensitive = options.get('case_sensitive', self.case_sensitive)
        self.enabled = options.get('enabled', self.enabled)

    def match(self, message):
        """
        Returns True if message matches our banphrase.
        Otherwise it returns False
        Respects case-sensitiveness option
        """
        if self.case_sensitive:
            return self.phrase in message
        else:
            return self.phrase.lower() in message.lower()

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

class BanphraseData(Base):
    __tablename__ = 'tb_banphrase_data'

    banphrase_id = Column(Integer,
            ForeignKey('tb_banphrase.id'),
            primary_key=True,
            autoincrement=False)
    num_uses = Column(Integer, nullable=False, default=0)
    added_by = Column(Integer, nullable=True)

    user = relationship('User',
            primaryjoin='User.id==BanphraseData.added_by',
            foreign_keys='User.id',
            uselist=False,
            cascade='',
            lazy='noload')

    def __init__(self, banphrase_id, **options):
        self.banphrase_id = banphrase_id
        self.num_uses = 0
        self.added_by = None

        self.set(**options)

    def set(self, **options):
        self.num_uses = options.get('num_uses', self.num_uses)
        self.added_by = options.get('added_by', self.added_by)

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
            banphrase_id = int(data['banphrase_id'])
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
            banphrase_id = int(data['banphrase_id'])
        except (KeyError, ValueError):
            log.warn('No banphrase ID found in on_banphrase_remove')
            return False

        removed_banphrase = find(lambda banphrase: banphrase.id == banphrase_id, self.banphrases)
        if removed_banphrase:
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

        if banphrase.permanent is True:
            # Permanently ban user
            punishment = 'permanently banned'
            self.bot.ban(user.username)
        else:
            # Timeout user
            timeout_length, punishment = user.timeout(banphrase.length, self.bot, use_warnings=banphrase.warning)

            """ Finally, time out the user for whatever timeout length was required. """
            self.bot.timeout(user.username, timeout_length)

        if banphrase.notify is True:
            """ Last but not least, notify the user why he has been timed out
                if the banphrase wishes it. """
            notification_msg = 'You have been {punishment} because your message matched the "{banphrase.name}" banphrase.'.format(punishment=punishment, banphrase=banphrase)
            self.bot.whisper(user.username, notification_msg)

    def check_message(self, message):
        match = find(lambda banphrase: banphrase.match(message), self.enabled_banphrases)
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
        parser.add_argument('--name', nargs='+', dest='name')
        parser.set_defaults(length=None,
                notify=None,
                permanent=None,
                case_sensitive=None,
                warning=None)

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
