import argparse
import logging
from collections import UserList

from pajbot import utils
from pajbot.managers.db import DBManager
from pajbot.models.deck import Deck

log = logging.getLogger(__name__)


class DeckManager(UserList):
    def __init__(self):
        UserList.__init__(self)
        self.current_deck = None
        self.reload()

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

        return None

    def refresh_current_deck(self):
        self.current_deck = None
        for deck in self.data:
            if self.current_deck is None or deck.last_used > self.current_deck.last_used:
                self.current_deck = deck

    def remove_deck(self, deck):
        self.data.remove(deck)
        with DBManager.create_session_scope_nc(expire_on_commit=False) as db_session:
            db_session.delete(deck)
            db_session.commit()

        if deck == self.current_deck:
            log.info("refreshing current deck")
            self.refresh_current_deck()

    def set_current_deck(self, deck_link):
        # Loop through our already loaded decks
        now = utils.now()
        for deck in self.data:
            # Is this deck link already i use?
            if deck_link == deck.link:
                self.current_deck = deck
                self.update_deck(deck, times_used=deck.times_used + 1, last_used=now)
                return deck, False

        # No old deck matched the link, create a new deck!
        with DBManager.create_session_scope_nc(expire_on_commit=False) as db_session:
            deck = Deck()
            deck.set(link=deck_link, times_used=1, first_used=now, last_used=now)
            self.current_deck = deck
            self.data.append(deck)
            db_session.add(deck)
            db_session.commit()
            db_session.expunge(deck)
        return deck, True

    @staticmethod
    def update_deck(deck, **options):
        with DBManager.create_session_scope_nc(expire_on_commit=False) as db_session:
            db_session.add(deck)
            deck.set(**options)
            db_session.commit()
            db_session.expunge(deck)

    @staticmethod
    def parse_update_arguments(message):
        parser = argparse.ArgumentParser()
        parser.add_argument("--id", type=int, dest="id")
        parser.add_argument("--name", nargs="+", dest="name")
        parser.add_argument("--class", dest="class")
        parser.add_argument("--link", dest="link")

        try:
            args, unknown = parser.parse_known_args(message.split())
        except SystemExit:
            return False, False
        except:
            log.exception("Unhandled exception in add_command")
            return False, False

        # Strip options of any values that are set as None
        options = {k: v for k, v in vars(args).items() if v is not None}
        if "name" in options:
            options["name"] = " ".join(options["name"])
        response = " ".join(unknown)

        return options, response

    def reload(self):
        self.data = []
        with DBManager.create_session_scope_nc(expire_on_commit=False) as db_session:
            for deck in db_session.query(Deck).order_by(Deck.last_used.desc()):
                if self.current_deck is None:
                    self.current_deck = deck
                self.data.append(deck)
                db_session.expunge(deck)

            db_session.expunge_all()
