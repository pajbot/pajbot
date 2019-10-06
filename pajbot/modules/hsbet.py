import datetime
import logging

from requests import HTTPError
from sqlalchemy.orm import joinedload

from pajbot import utils
from pajbot.apiwrappers.trackobot import TrackOBotAPI
from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.command import Command
from pajbot.models.hsbet import HSBetBet, HSGameOutcome
from pajbot.models.hsbet import HSBetGame
from pajbot.models.user import User
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class HSBetModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Hearthstone Betting"
    DESCRIPTION = "Enables betting on Hearthstone game outcomes with !hsbet"
    CATEGORY = "Game"
    SETTINGS = [
        ModuleSetting(
            key="trackobot_username",
            label="Track-o-bot Username",
            type="text",
            required=True,
            placeholder="Username",
            default="",
            constraints={"min_str_len": 2, "max_str_len": 32},
        ),
        ModuleSetting(
            key="trackobot_api_key",
            label="Track-o-bot API Key",
            type="text",
            required=True,
            placeholder="API Key",
            default="",
            constraints={"min_str_len": 2, "max_str_len": 32},
        ),
        ModuleSetting(
            key="time_until_bet_closes",
            label="Seconds until betting closes",
            type="number",
            required=True,
            placeholder="Seconds until betting closes",
            default=60,
            constraints={"min_value": 10, "max_value": 180},
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

        self.api = TrackOBotAPI()
        self.first_fetch = True
        self.last_game = None

        self.poll_job = ScheduleManager.execute_every(15, self.poll_trackobot)
        self.poll_job.pause()
        self.reminder_job = ScheduleManager.execute_every(1, self.reminder_bet)
        self.reminder_job.pause()

    def get_current_game(self, db_session, with_bets=False, with_users=False):
        query = db_session.query(HSBetGame).filter(HSBetGame.is_running)

        # with_bets and with_users are just optimizations for the querying.
        # If a code path knows it's going to need to load the bets and users for each bet,
        # we can load them eagerly with a proper SQL JOIN instead of lazily later,
        # to make that code path faster
        if with_bets:
            query = query.options(joinedload(HSBetGame.bets))
        if with_users:
            query = query.options(joinedload(HSBetGame.bets).joinedload(HSBetBet.user))

        current_game = query.one_or_none()
        if current_game is None:
            current_game = HSBetGame()
            db_session.add(current_game)
            db_session.flush()  # so we get current_game.id set
        return current_game

    def reminder_bet(self):
        with DBManager.create_session_scope() as db_session:
            current_game = db_session.query(HSBetGame).filter(HSBetGame.betting_open).one_or_none()
            if current_game is None:
                return

            seconds_until_bet_closes = int((current_game.bet_deadline - utils.now()).total_seconds()) - 1

            def win_lose_statistic():
                points_stats = current_game.get_points_by_outcome(db_session)
                return f"{points_stats[HSGameOutcome.win]}/{points_stats[HSGameOutcome.loss]}"

            if (seconds_until_bet_closes % 10) == 0 and seconds_until_bet_closes > 0:
                self.bot.me(
                    f"The hearthstone betting closes in {seconds_until_bet_closes} seconds. Current win/lose points: {win_lose_statistic()}"
                )
            elif seconds_until_bet_closes == 5:
                self.bot.me(
                    f"The hearthstone betting closes in 5 seconds... Current win/lose points: {win_lose_statistic()}"
                )
            elif seconds_until_bet_closes == 0:
                self.bot.me(
                    f"The hearthstone betting has been closed! No longer accepting bets. Closing with win/lose points: {win_lose_statistic()}"
                )

    def poll_trackobot(self):
        username = self.settings["trackobot_username"]
        token = self.settings["trackobot_api_key"]

        if len(username) == 0 or len(token) == 0:
            # module not configured with Track-O-Bot credentials,
            # we don't need to contact the API at all
            return

        try:
            latest_game = self.api.get_latest_game(username, token)
        except HTTPError as e:
            if e.response.status_code == 401:
                # avoid printing a huge stacktrace
                log.warning("Track-O-Bot: Unauthorized")
                return
            else:
                raise e

        self.bot.execute_now(self.poll_trackobot_stage2, latest_game)

    def detect_trackobot_game_change(self, new_game):
        old_game = self.last_game
        self.last_game = new_game

        if self.first_fetch:
            self.first_fetch = False
            return False
        return new_game is not None and old_game != new_game

    def poll_trackobot_stage2(self, trackobot_game):
        if not self.detect_trackobot_game_change(trackobot_game):
            return

        with DBManager.create_session_scope() as db_session:
            current_game = self.get_current_game(db_session, with_bets=True, with_users=True)

            current_game.trackobot_id = trackobot_game.id
            current_game.outcome = trackobot_game.outcome

            points_by_outcome = current_game.get_points_by_outcome(db_session)
            total_points_in_pot = sum(points_by_outcome.values())

            for bet in current_game.bets:
                correct_bet = bet.outcome == current_game.outcome

                if not correct_bet:
                    # lost the bet
                    bet.profit = -bet.points
                    self.bot.whisper(
                        bet.user, f"You bet {bet.points} points on the wrong outcome, so you lost it all. :("
                    )
                else:
                    # won the bet
                    investment_ratio = bet.points / points_by_outcome[bet.outcome]
                    # pot_cut includes the user's initial investment
                    pot_cut = int(investment_ratio * total_points_in_pot)
                    # profit is just how much they won
                    bet.profit = pot_cut - bet.points
                    bet.user.points = User.points + pot_cut
                    self.bot.whisper(
                        bet.user,
                        f"You bet {bet.points} points on the right outcome, that leaves you with a profit of {bet.profit} points! (Your bet was {investment_ratio * 100:.2f}% of the total pot)",
                    )
                    HandlerManager.trigger("on_user_win_hs_bet", user=bet.user, points_won=bet.profit)

            winning_points = sum(
                points for outcome, points in points_by_outcome.items() if outcome == current_game.outcome
            )
            losing_points = sum(
                points for outcome, points in points_by_outcome.items() if outcome != current_game.outcome
            )
            end_message = f"The game ended as a {trackobot_game.outcome.name}. {points_by_outcome[HSGameOutcome.win]} points bet on win, {points_by_outcome[HSGameOutcome.loss]} points bet on loss."

            # don't want to divide by 0
            if winning_points != 0:
                ratio = losing_points / winning_points * 100
                end_message += f" Winners can expect a {ratio:.2f}% return on their bet points."
            else:
                end_message += " Nobody won any points. KKona"

            self.bot.me(end_message)

            # so we can create a new game
            db_session.flush()

            self.bot.me("A new game has begun! Vote with !hsbet win/lose POINTS")
            current_game = self.get_current_game(db_session)
            time_limit = self.settings["time_until_bet_closes"]
            current_game.bet_deadline = utils.now() + datetime.timedelta(seconds=time_limit)

            bets_statistics = current_game.get_bets_by_outcome(db_session)

            payload = {"time_left": time_limit, **{key.name: value for key, value in bets_statistics.items()}}
            self.bot.websocket_manager.emit("hsbet_new_game", data=payload)

    def command_bet(self, bot, source, message, **rest):
        if message is None:
            return False

        with DBManager.create_session_scope() as db_session:
            current_game = self.get_current_game(db_session)

            if not current_game.betting_open:
                # Don't send that whisper if the game has never been open before
                if current_game.bet_deadline is not None:
                    bot.whisper(source, "The game is too far along for you to bet on it. Wait until the next game!")
                return False

            msg_parts = message.split(" ")

            outcome_input = msg_parts[0].lower()
            if outcome_input in {"win", "winner"}:
                bet_for = HSGameOutcome.win
            elif outcome_input in {"lose", "loss", "loser", "loose"}:
                bet_for = HSGameOutcome.loss
            else:
                bot.whisper(source, "Invalid bet. Usage: !hsbet win/loss POINTS")
                return False

            try:
                points = int(msg_parts[1])
            except (IndexError, ValueError, TypeError):
                bot.whisper(source, "Invalid bet. Usage: !hsbet win/loss POINTS")
                return False

            if points < 0:
                bot.whisper(source, "You cannot bet negative points.")
                return False

            max_bet = self.settings["max_bet"]
            if points > max_bet:
                bot.whisper(source, f"You cannot bet more than {max_bet} points, please try again!")
                return False

            if not source.can_afford(points):
                bot.whisper(source, f"You don't have {points} points to bet")
                return False

            user_bet = db_session.query(HSBetBet).filter_by(game_id=current_game.id, user_id=source.id).one_or_none()
            if user_bet is not None:
                bot.whisper(source, "You have already bet on this game. Wait until the next game starts!")
                return False

            user_bet = HSBetBet(game_id=current_game.id, user_id=source.id, outcome=bet_for, points=points)
            db_session.add(user_bet)
            source.points -= points
            bot.whisper(source, f"You have bet {points} points on this game resulting in a {bet_for.name}.")

            if points > 0:
                # this creates a dict { "win": 0, "loss": 1234 } or { "win": 1234, "loss": 0 }
                # because the `bet_for.name` dynamically overwrites one of the two constants declared before
                payload = {"win": 0, "loss": 0, bet_for.name: points}
                self.bot.websocket_manager.emit("hsbet_update_data", data=payload)

    def command_open(self, bot, message, **rest):
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

        with DBManager.create_session_scope() as db_session:
            current_game = self.get_current_game(db_session)
            current_game.bet_deadline = utils.now() + datetime.timedelta(seconds=time_limit)

            bets_statistics = current_game.get_bets_by_outcome(db_session)

            payload = {"time_left": time_limit, **{key.name: value for key, value in bets_statistics.items()}}
            self.bot.websocket_manager.emit("hsbet_new_game", data=payload)

            bot.me(
                f"The bet for the current hearthstone game is open again! You have {time_limit} seconds to vote !hsbet win/lose POINTS"
            )

    def command_close(self, bot, **rest):
        with DBManager.create_session_scope() as db_session:
            current_game = self.get_current_game(db_session, with_bets=True, with_users=True)
            for bet in current_game.bets:
                bet.user.points = User.points + bet.points
                if bet.points > 0:
                    bot.whisper(
                        bet.user,
                        f"Your HS bet of {bet.points} points has been refunded because the bet has been cancelled.",
                    )
            db_session.delete(current_game)

    def command_stats(self, bot, source, **rest):
        with DBManager.create_session_scope() as db_session:
            current_game = self.get_current_game(db_session)
            points_stats = current_game.get_points_by_outcome(db_session)
            bot.whisper(
                source, f"Current win/lose points: {points_stats[HSGameOutcome.win]}/{points_stats[HSGameOutcome.loss]}"
            )

    def load_commands(self, **rest):
        self.commands["hsbet"] = Command.multiaction_command(
            level=100,
            default="bet",
            fallback="bet",
            delay_all=0,
            delay_user=0,
            can_execute_with_whisper=True,
            commands={
                "bet": Command.raw_command(self.command_bet, delay_all=0, delay_user=10, can_execute_with_whisper=True),
                "open": Command.raw_command(
                    self.command_open, level=500, delay_all=0, delay_user=0, can_execute_with_whisper=True
                ),
                "close": Command.raw_command(
                    self.command_close, level=500, delay_all=0, delay_user=0, can_execute_with_whisper=True
                ),
                "stats": Command.raw_command(
                    self.command_stats, level=100, delay_all=0, delay_user=10, can_execute_with_whisper=True
                ),
            },
        )

    def enable(self, bot):
        if bot:
            self.poll_job.resume()
            self.reminder_job.resume()

    def disable(self, bot):
        if bot:
            self.poll_job.pause()
            self.reminder_job.pause()
            self.first_fetch = True
            self.last_game = None
