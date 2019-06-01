from flask import render_template

from pajbot.managers.db import DBManager
from pajbot.models.deck import Deck


def init(app):
    @app.route("/decks/")
    def decks():
        session = DBManager.create_session()
        top_decks = []
        for deck in session.query(Deck).order_by(Deck.last_used.desc(), Deck.first_used.desc())[:25]:
            top_decks.append(deck)
        session.close()
        return render_template("decks/all.html", top_decks=top_decks, deck_class=None)

    @app.route("/decks/druid/")
    def decks_druid():
        session = DBManager.create_session()
        decks = (
            session.query(Deck)
            .filter_by(deck_class="druid")
            .order_by(Deck.last_used.desc(), Deck.first_used.desc())
            .all()
        )
        session.close()
        return render_template("decks/by_class.html", decks=decks, deck_class="Druid")

    @app.route("/decks/hunter/")
    def decks_hunter():
        session = DBManager.create_session()
        decks = (
            session.query(Deck)
            .filter_by(deck_class="hunter")
            .order_by(Deck.last_used.desc(), Deck.first_used.desc())
            .all()
        )
        session.close()
        return render_template("decks/by_class.html", decks=decks, deck_class="Hunter")

    @app.route("/decks/mage/")
    def decks_mage():
        session = DBManager.create_session()
        decks = (
            session.query(Deck)
            .filter_by(deck_class="mage")
            .order_by(Deck.last_used.desc(), Deck.first_used.desc())
            .all()
        )
        session.close()
        return render_template("decks/by_class.html", decks=decks, deck_class="Mage")

    @app.route("/decks/paladin/")
    def decks_paladin():
        session = DBManager.create_session()
        decks = (
            session.query(Deck)
            .filter_by(deck_class="paladin")
            .order_by(Deck.last_used.desc(), Deck.first_used.desc())
            .all()
        )
        session.close()
        return render_template("decks/by_class.html", decks=decks, deck_class="Paladin")

    @app.route("/decks/priest/")
    def decks_priest():
        session = DBManager.create_session()
        decks = (
            session.query(Deck)
            .filter_by(deck_class="priest")
            .order_by(Deck.last_used.desc(), Deck.first_used.desc())
            .all()
        )
        session.close()
        return render_template("decks/by_class.html", decks=decks, deck_class="Priest")

    @app.route("/decks/rogue/")
    def decks_rogue():
        session = DBManager.create_session()
        decks = (
            session.query(Deck)
            .filter_by(deck_class="rogue")
            .order_by(Deck.last_used.desc(), Deck.first_used.desc())
            .all()
        )
        session.close()
        return render_template("decks/by_class.html", decks=decks, deck_class="Rogue")

    @app.route("/decks/shaman/")
    def decks_shaman():
        session = DBManager.create_session()
        decks = (
            session.query(Deck)
            .filter_by(deck_class="shaman")
            .order_by(Deck.last_used.desc(), Deck.first_used.desc())
            .all()
        )
        session.close()
        return render_template("decks/by_class.html", decks=decks, deck_class="Shaman")

    @app.route("/decks/warlock/")
    def decks_warlock():
        session = DBManager.create_session()
        decks = (
            session.query(Deck)
            .filter_by(deck_class="warlock")
            .order_by(Deck.last_used.desc(), Deck.first_used.desc())
            .all()
        )
        session.close()
        return render_template("decks/by_class.html", decks=decks, deck_class="Warlock")

    @app.route("/decks/warrior/")
    def decks_warrior():
        session = DBManager.create_session()
        decks = (
            session.query(Deck)
            .filter_by(deck_class="warrior")
            .order_by(Deck.last_used.desc(), Deck.first_used.desc())
            .all()
        )
        session.close()
        return render_template("decks/by_class.html", decks=decks, deck_class="Warrior")
