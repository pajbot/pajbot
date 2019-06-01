import datetime
import itertools
import logging

from numpy import random

from pajbot import utils
from pajbot.models.command import Command
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class BlackjackDeck:
    SUITS = "cdhs"
    RANKS = "23456789TJQKA"

    def __init__(self):
        self.cards = ["".join(card) for card in itertools.product(self.RANKS, self.SUITS)]
        random.shuffle(self.cards)

    def __repr__(self):
        return "Cards: {}".format(self.cards)


class BlackjackGame:
    def __init__(self, bot, player, bet):
        self.bot = bot
        self.player = player
        self.bet = bet
        self.deck = BlackjackDeck()
        self.state = "new_game"

    def print_state(self):
        log.info("bot: {}".format(self.bot))
        log.info("player: {}".format(self.player))
        log.info("bet: {}".format(self.bet))
        log.info("state: {}".format(self.state))
        log.info("deck: {}".format(self.deck))

    def deal(self):
        pass
        # Deal cards


class BlackjackModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Blackjack"
    DESCRIPTION = "Enables the users to play Blackjack with the bot using the !blackjack command"
    CATEGORY = "Game"
    SETTINGS = [
        ModuleSetting(key="reply_in_whispers", label="Reply in whispers", type="boolean", required=True, default=False),
        ModuleSetting(
            key="only_play_in_whispers",
            label="Only accept commands through whispers",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="max_bet",
            label="Max bet in points",
            type="number",
            required=True,
            placeholder="Max bet",
            default=5000,
            constraints={"min_value": 500, "max_value": 30000},
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)
        self.games = {}

    def command_bet(self, **options):
        bot = options["bot"]
        source = options["source"]
        message = options["message"]

        if message is None:
            return False

        if self.last_game_start is None:
            return False

        if not self.is_betting_open():
            bot.whisper(source.username, "The game is too far along for you to bet on it. Wait until the next game!")
            return False

        msg_parts = message.split(" ")
        if msg_parts == 0:
            bot.whisper(source.username, "Usage: !hsbet win/lose POINTS")
            return False

        outcome = msg_parts[0].lower()
        bet_for_win = False

        if outcome in ("win", "winner"):
            bet_for_win = True
        elif outcome in ("lose", "loss", "loser"):
            bet_for_win = False
        else:
            bot.whisper(source.username, "Invalid bet. Usage: !hsbet win/loss POINTS")
            return False

        points = 0
        try:
            points = int(msg_parts[1])
        except (IndexError, ValueError, TypeError):
            bot.whisper(source.username, "Invalid bet. Usage: !hsbet win/loss POINTS")
            return False

        if points < 0:
            bot.whisper(source.username, "You cannot bet negative points.")
            return False

        if points > self.settings["max_bet"]:
            bot.whisper(
                source.username,
                "You cannot bet more than {} points, please try again!".format(self.settings["max_bet"]),
            )
            return False

        if not source.can_afford(points):
            bot.whisper(source.username, "You don't have {} points to bet".format(points))
            return False

        if source.username in self.bets:
            bot.whisper(source.username, "You have already bet on this game. Wait until the next game starts!")
            return False

        source.create_debt(points)
        self.bets[source.username] = (bet_for_win, points)
        bot.whisper(
            source.username,
            "You have bet {} points on this game resulting in a {}.".format(points, "win" if bet_for_win else "loss"),
        )

    def command_open(self, **options):
        bot = options["bot"]
        message = options["message"]

        time_limit = self.settings["time_until_bet_closes"]

        if message:
            msg_split = message.split(" ")
            try:
                time_limit = int(msg_split[0])

                if time_limit < 10:
                    time_limit = 10
                elif time_limit > 180:
                    time_limit = 180
            except (ValueError, TypeError):
                pass

        self.last_game_start = utils.now() + datetime.timedelta(seconds=time_limit)

        bot.me(
            "The bet for the current hearthstone game is open again! You have {} seconds to vote !hsbet win/lose POINTS".format(
                time_limit
            )
        )

    def command_close(self, **options):
        bot = options["bot"]

        self.last_game_start = utils.now() - datetime.timedelta(seconds=10)

        for username in self.bets:
            _, points = self.bets[username]
            user = self.bot.users[username]
            user.remove_debt(points)
            bot.whisper(
                username,
                "Your HS bet of {} points has been refunded because the bet has been cancelled.".format(points),
            )
        self.bets = {}

    def load_commands(self, **options):
        self.commands["blackjack"] = Command.multiaction_command(
            level=100,
            default="bet",
            fallback="bet",
            delay_all=0,
            delay_user=0,
            can_execute_with_whisper=True,
            commands={
                "start": Command.raw_command(
                    self.command_bet, delay_all=0, delay_user=10, can_execute_with_whisper=True
                ),
                "open": Command.raw_command(
                    self.command_open, level=500, delay_all=0, delay_user=0, can_execute_with_whisper=True
                ),
                "close": Command.raw_command(
                    self.command_close, level=500, delay_all=0, delay_user=0, can_execute_with_whisper=True
                ),
            },
        )

    def enable(self, bot):
        if bot:
            self.job.resume()
            self.reminder_job.resume()

    def disable(self, bot):
        if bot:
            self.job.pause()
            self.reminder_job.pause()
