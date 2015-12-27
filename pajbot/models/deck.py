import logging
import datetime
import argparse
from collections import UserList

from pajbot.tbutil import time_ago
from pajbot.models.db import DBManager, Base

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import desc

log = logging.getLogger('pajbot')


class Deck(Base):
    __tablename__ = 'tb_deck'

    id = Column(Integer, primary_key=True)
    name = Column(String(128))
    deck_class = Column('class', String(128))
    link = Column(String(256), nullable=False)
    first_used = Column(DateTime, nullable=False)
    last_used = Column(DateTime, nullable=False)
    times_used = Column(Integer, nullable=False, default=1)

    def __init__(self):
        self.id = None
        self.name = ''
        self.deck_class = 'undefined'
        self.link = None
        self.times_used = 1

    def set(self, **options):
        self.name = options.get('name', self.name)
        self.deck_class = options.get('class', self.deck_class)
        self.link = options.get('link', self.link)
        self.times_used = options.get('times_used', self.times_used)
        self.first_used = options.get('first_used', self.first_used)
        self.last_used = options.get('last_used', self.last_used)

    @property
    def last_used_ago(self):
        return time_ago(self.last_used, 'long')

    @property
    def first_used_ago(self):
        return time_ago(self.last_used, 'long')


class DeckManager(UserList):
    def __init__(self):
        UserList.__init__(self)
        self.db_session = DBManager.create_session()
        self.current_deck = None

    def find(self, id=None, link=None):
        if id is not None:
            for deck in self.data:
                if id == deck.id:
                    return deck
        elif link is not None:
            for deck in self.data:
                if link == deck.link:
                    return deck
        return None

    def action_get_curdeck(self, key, extra={}):
        if self.current_deck is not None:
            return getattr(self.current_deck, key, None)
        else:
            return None

    def refresh_current_deck(self):
        self.current_deck = None
        for deck in self.data:
            if self.current_deck is None or deck.last_used > self.current_deck.last_used:
                self.current_deck = deck

    def remove_deck(self, deck):
        self.data.remove(deck)
        self.db_session.delete(deck)
        self.commit()
        if deck == self.current_deck:
            log.info('refreshing current deck')
            self.refresh_current_deck()

    def set_current_deck(self, deck_link):
        for deck in self.data:
            if deck_link == deck.link:
                self.current_deck = deck
                deck.times_used += 1
                deck.last_used = datetime.datetime.now()
                return deck, False

        deck = Deck()
        deck.set(link=deck_link,
                times_used=1,
                first_used=datetime.datetime.now(),
                last_used=datetime.datetime.now())
        self.current_deck = deck
        self.db_session.add(deck)
        self.data.append(deck)
        self.commit()
        return deck, True

    def parse_update_arguments(self, message):
        parser = argparse.ArgumentParser()
        parser.add_argument('--id', type=int, dest='id')
        parser.add_argument('--name', nargs='+', dest='name')
        parser.add_argument('--class', dest='class')
        parser.add_argument('--link', dest='link')

        try:
            args, unknown = parser.parse_known_args(message.split())
        except SystemExit:
            return False, False
        except:
            log.exception('Unhandled exception in add_command')
            return False, False

        # Strip options of any values that are set as None
        options = {k: v for k, v in vars(args).items() if v is not None}
        if 'name' in options:
            options['name'] = ' '.join(options['name'])
        response = ' '.join(unknown)

        return options, response

    def commit(self):
        self.db_session.commit()

    def reload(self):
        self.data = []
        for deck in self.db_session.query(Deck).order_by(desc(Deck.last_used)):
            if self.current_deck is None:
                self.current_deck = deck
            self.data.append(deck)

        log.info('Loaded {0} decks'.format(len(self.data)))
        return self
