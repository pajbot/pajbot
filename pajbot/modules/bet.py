import logging

from sqlalchemy.orm import joinedload

from pajbot import utils
from pajbot.exc import InvalidPointAmount
from pajbot.managers.db import DBManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.bet import BetBet, BetGameOutcome, BetGame
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.models.user import User
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)

WIDGET_ID = 2


class BetModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Betting"
    DESCRIPTION = "Enables betting on games with !bet"
    CATEGORY = "Game"

    SETTINGS = [
        ModuleSetting(  # Not required
            key="max_return", label="Maximum return odds", type="number", placeholder="", default="20"
        ),
        ModuleSetting(  # Not required
            key="min_return", label="Minimum return odds", type="text", placeholder="", default="1.10"
        ),
        ModuleSetting(key="max_bet", label="Maximum bet", type="number", placeholder="", default="3000"),
    ]

    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot
        self.lock_schedule = None
        self.close_schedule = None
        self.spectating = False

    def reminder_bet(self):
        with DBManager.create_session_scope() as db_session:
            current_game = db_session.query(BetGame).filter(BetGame.betting_open).one_or_none()
            if not current_game:
                return

            self.bot.me("monkaS 👉 🕒 place your bets people")
            self.bot.websocket_manager.emit(
                event="notification", widget_id=WIDGET_ID, data={"message": "monkaS 👉 🕒 place your bets people"}
            )

    def get_current_game(self, db_session, with_bets=False, with_users=False):
        query = db_session.query(BetGame).filter(BetGame.is_running)

        if with_bets:
            query = query.options(joinedload(BetGame.bets))
        if with_users:
            query = query.options(joinedload(BetGame.bets).joinedload(BetBet.user))

        current_game = query.one_or_none()
        if current_game is None:
            current_game = BetGame()
            db_session.add(current_game)
            db_session.flush()

        return current_game

    @staticmethod
    def create_solve_formula(x, y):
        return 1.0 + (float(x) / (float(y)))

    def get_odds_ratio(self, points_by_outcome):
        lossPoints = points_by_outcome[BetGameOutcome.loss]
        winPoints = points_by_outcome[BetGameOutcome.win]

        if lossPoints == 0:
            lossPoints = 1
        if winPoints == 0:
            winPoints = 1

        winRatio = round(self.create_solve_formula(lossPoints, winPoints), 2)
        if self.settings["max_return"] and winRatio > float(self.settings["max_return"]):
            winRatio = round(float(self.settings["max_return"]), 2)
        elif self.settings["min_return"] and winRatio < float(self.settings["min_return"]):
            winRatio = round(float(self.settings["min_return"]), 2)

        lossRatio = round(self.create_solve_formula(winPoints, lossPoints), 2)
        if self.settings["max_return"] and lossRatio > float(self.settings["max_return"]):
            lossRatio = round(float(self.settings["max_return"]), 2)
        elif self.settings["min_return"] and lossRatio < float(self.settings["min_return"]):
            lossRatio = round(float(self.settings["min_return"]), 2)

        ratioList = {BetGameOutcome.win: winRatio, BetGameOutcome.loss: lossRatio}

        return ratioList

    def spread_points(self, gameResult):
        with DBManager.create_session_scope() as db_session:
            # What is faster? Doing it like this or with a generator afterwards?
            winners = 0
            losers = 0
            current_game = self.get_current_game(db_session, with_bets=True, with_users=True)

            current_game.outcome = gameResult
            points_by_outcome = current_game.get_points_by_outcome(db_session)
            investment_ratios = self.get_odds_ratio(points_by_outcome)
            total_winnings = 0
            total_losings = 0
            for bet in current_game.bets:
                if bet.outcome == current_game.outcome:
                    winners += 1
                    investment_ratio = investment_ratios[bet.outcome]
                    bet.profit = int(bet.points * (investment_ratio - 1))
                    bet.user.points += int(bet.points + bet.profit)
                    total_winnings += bet.profit
                    self.bot.whisper(
                        bet.user,
                        f"You bet {bet.points} points on the correct outcome and gained an extra {bet.profit} points, you now have {bet.user.points} points PogChamp",
                    )
                else:
                    losers += 1
                    bet.profit = -bet.points
                    total_losings += -bet.profit
                    self.bot.whisper(
                        bet.user,
                        f"You bet {bet.points} points on the wrong outcome, so you lost it all :( . You now have {bet.user.points} points sadKEK",
                    )

            startString = f"The game ended as a {gameResult.name}. {winners} users won an extra {total_winnings} points, while {losers} users lost {total_losings} points."

            if self.spectating:
                resultString = startString[:20] + "radiant " + startString[20:]
            else:
                resultString = startString

            # Just to make sure
            current_game.bets_closed = True
            self.spectating = False

            self.bot.websocket_manager.emit(
                event="notification", widget_id=WIDGET_ID, data={"message": resultString, "length": 8}
            )
            self.bot.me(resultString)

            db_session.flush()
            self.bot.websocket_manager.emit(event="bet_show_bets", widget_id=WIDGET_ID)
            if self.close_schedule:
                try:
                    self.close_schedule.remove()
                except:
                    pass
            self.close_schedule = ScheduleManager.execute_delayed(
                15, self.bot.websocket_manager.emit, args=["bet_close_game", WIDGET_ID]
            )

    def lock_bets(self):
        self.lock_schedule = None
        if self.close_schedule:
            try:
                self.close_schedule.remove()
            except:
                pass
        self.close_schedule = None
        with DBManager.create_session_scope() as db_session:
            current_game = self.get_current_game(db_session)
            if current_game.bets_closed:
                return False

            points_by_outcome = current_game.get_points_by_outcome(db_session)
            investment_ratios = self.get_odds_ratio(points_by_outcome)
            winRatio = investment_ratios[BetGameOutcome.win]
            lossRatio = investment_ratios[BetGameOutcome.loss]

            self.bot.me(
                f"The betting for the current game has been closed! Winners can expect {winRatio} (win bettors) or {lossRatio} (loss bettors) point return on their bet"
            )
            self.bot.websocket_manager.emit(
                event="notification",
                widget_id=WIDGET_ID,
                data={"message": "The betting for the current game has been closed!"},
            )

            self.close_schedule = ScheduleManager.execute_delayed(
                15, self.bot.websocket_manager.emit, args=["bet_close_game", WIDGET_ID]
            )
            current_game.bets_closed = True

    def start_game(self, openString=None):
        with DBManager.create_session_scope() as db_session:
            current_game = db_session.query(BetGame).filter(BetGame.is_running).one_or_none()

            if current_game is None:
                current_game = BetGame()
                db_session.add(current_game)
                db_session.flush()
            elif not current_game.betting_open:
                current_game.bets_closed = False
                openString = "The betting has been reopened for this game"
            else:
                self.bot.say("Betting is already open Pepega")
                return False

            if not openString:
                openString = "A new game has begun! Vote with !bet win/lose POINTS"
            if self.close_schedule:
                try:
                    self.close_schedule.remove()
                except:
                    pass
            self.close_schedule = None
            self.bot.websocket_manager.emit(event="notification", widget_id=WIDGET_ID, data={"message": openString})
            if not self.spectating:
                self.bot.websocket_manager.emit(event="bet_new_game", widget_id=WIDGET_ID)

            current_points = current_game.get_points_by_outcome(db_session)
            current_bets = current_game.get_bets_by_outcome(db_session)

            payload = {
                "win_points": current_points[BetGameOutcome.win],
                "loss_points": current_points[BetGameOutcome.loss],
                "win_bettors": current_bets[BetGameOutcome.win],
                "loss_bettors": current_bets[BetGameOutcome.loss],
            }

            self.bot.websocket_manager.emit(event="bet_update_data", widget_id=WIDGET_ID, data=payload)

            self.bot.me(openString)
            return True

    def command_open(self, message, **rest):
        openString = "A new game has begun! Vote with !bet win/lose POINTS"

        if message and any(specHint in message for specHint in ["dire", "radi", "spectat"]):
            self.spectating = True
            openString += ". Reminder to bet with radiant/dire instead of win/loss"

        return self.start_game(openString)

    def command_stats(self, bot, **rest):
        with DBManager.create_session_scope() as db_session:
            current_game = db_session.query(BetGame).filter(BetGame.is_running).one_or_none()
            if not current_game:
                bot.say("No bet is currently running WeirdChamp")
                return False

            points_stats = current_game.get_points_by_outcome(db_session)
            bet_stats = current_game.get_bets_by_outcome(db_session)
            bot.say(
                f"{bet_stats[BetGameOutcome.win]} users bet {points_stats[BetGameOutcome.win]} points on win and {bet_stats[BetGameOutcome.loss]} users bet {points_stats[BetGameOutcome.loss]} points on loss"
            )

    def command_stats_ratio(self, bot, source, message, **rest):
        with DBManager.create_session_scope() as db_session:
            current_game = db_session.query(BetGame).filter(BetGame.is_running).one_or_none()
            if not current_game:
                bot.say("No bet is currently running WeirdChamp")
                return False

            points_by_outcome = current_game.get_points_by_outcome(db_session)
            investment_ratios = self.get_odds_ratio(points_by_outcome)
            winRatio = investment_ratios[BetGameOutcome.win]
            lossRatio = investment_ratios[BetGameOutcome.loss]

            bot.say(
                f"The current ratios are {winRatio} (win bettors) and {lossRatio} (loss bettors) point return on their bet"
            )

    def command_close(self, bot, source, message, **rest):
        with DBManager.create_session_scope() as db_session:
            current_game = db_session.query(BetGame).filter(BetGame.is_running).one_or_none()
            if not current_game:
                bot.say(f"{source}, no bet currently exists")
                return False

            if current_game.betting_open:
                if self.lock_schedule:
                    try:
                        self.lock_schedule.remove()
                    except:
                        pass
                self.lock_schedule = None
                count_down = 15
                if message and message.isdigit():
                    count_down = 15 if int(message) < 0 else int(message)
                if count_down > 0:
                    bot.me(f"Betting will be locked in {count_down} seconds! Place your bets people monkaS")

                self.lock_schedule = ScheduleManager.execute_delayed(count_down, self.lock_bets)
            elif message:
                split_message = message.split(" ")
                outcome = None
                if len(split_message) > 0:
                    for item in split_message:
                        outcome = "l" if "l" in item.lower() or "dire" in item.lower() else None
                        if not outcome:
                            outcome = "w" if "w" in item.lower() or "radi" in item.lower() else None
                        if outcome:
                            break
                if outcome:
                    if outcome == "l":
                        bot.execute_now(self.spread_points, BetGameOutcome.loss)
                    else:
                        bot.execute_now(self.spread_points, BetGameOutcome.win)
                else:
                    bot.say(f"Are you pretending {source}?")
                    return False
                self.spectating = False
            else:
                bot.say("WTFF")

    def command_restart(self, bot, message, **rest):
        reason = message if message else "No reason given EleGiggle"
        with DBManager.create_session_scope() as db_session:
            current_game = self.get_current_game(db_session, with_bets=True, with_users=True)
            for bet in current_game.bets:
                bet.user.points = User.points + bet.points
                bot.whisper(
                    bet.user, f"Your {bet.points} points bet has been refunded. The reason given is: '{reason}'"
                )

                db_session.delete(bet)

            current_game.timestamp = utils.now()

        self.spectating = False

        bot.me("All your bets have been refunded and betting has been restarted.")

    def command_stop_bet(self, bot, message, **rest):
        reason = message if message else "No reason given EleGiggle"
        with DBManager.create_session_scope() as db_session:
            current_game = self.get_current_game(db_session, with_bets=True, with_users=True)
            for bet in current_game.bets:
                bet.user.points = User.points + bet.points
                bot.whisper(
                    bet.user, f"Your {bet.points} points bet has been refunded. The reason given is: '{reason}'"
                )

                db_session.delete(bet)

            db_session.delete(current_game)

        self.spectating = False
        if self.close_schedule:
            try:
                self.close_schedule.remove()
            except:
                pass
        self.close_schedule = ScheduleManager.execute_now(
            self.bot.websocket_manager.emit, args=["bet_close_game", WIDGET_ID]
        )

        bot.me("All your bets have been refunded and betting has been closed.")

    def command_betstatus(self, bot, **rest):
        with DBManager.create_session_scope() as db_session:
            current_game = db_session.query(BetGame).filter(BetGame.is_running).one_or_none()

            if not current_game:
                bot.say("There is no bet running")
            elif current_game.betting_open:
                bot.say("Betting is open")
            elif current_game.is_running:
                bot.say("There is currently a bet with points not awarded yet")

    def command_bet(self, bot, source, message, **rest):
        if message is None:
            return False

        with DBManager.create_session_scope() as db_session:
            current_game = db_session.query(BetGame).filter(BetGame.is_running).one_or_none()
            if not current_game:
                bot.whisper(source, "There is currently no bet")
                return False

            if current_game.betting_open is False:
                bot.whisper(source, "Betting is not currently open. Wait until the next game :\\")
                return False

            msg_parts = message.split(" ")

            outcome_input = msg_parts[0].lower()
            if outcome_input in {"win", "winner", "radiant"}:
                bet_for = BetGameOutcome.win
            elif outcome_input in {"lose", "loss", "loser", "loose", "dire"}:
                bet_for = BetGameOutcome.loss
            else:
                bot.whisper(source, "Invalid bet. Usage: !bet win/loss POINTS")
                return False

            try:
                points = int(utils.parse_points_amount(source, msg_parts[1]))
                if points > int(self.settings["max_bet"]):
                    points = int(self.settings["max_bet"])
            except InvalidPointAmount as e:
                bot.whisper(source, f"Invalid bet. Usage: !bet win/loss POINTS. {e}")
                return False
            except IndexError:
                bot.whisper(source, "Invalid bet. Usage: !bet win/loss POINTS")
                return False

            if points < 1:
                bot.whisper(source, "You can't bet less than 1 point you goddamn pleb Bruh")
                return False

            if not source.can_afford(points):
                bot.whisper(source, f"You don't have {points} points to bet")
                return False

            user_bet = db_session.query(BetBet).filter_by(game_id=current_game.id, user_id=source.id).one_or_none()
            if user_bet is not None:
                bot.whisper(source, "You have already bet on this game. Wait until the next game starts!")
                return False

            user_bet = BetBet(game_id=current_game.id, user_id=source.id, outcome=bet_for, points=points)
            db_session.add(user_bet)
            source.points = source.points - points
            current_points = current_game.get_points_by_outcome(db_session)
            current_bets = current_game.get_bets_by_outcome(db_session)
            payload = {
                "win_points": current_points[BetGameOutcome.win] + (points if bet_for == BetGameOutcome.win else 0),
                "loss_points": current_points[BetGameOutcome.loss] + (points if bet_for == BetGameOutcome.loss else 0),
                "win_bettors": current_bets[BetGameOutcome.win] + (1 if bet_for == BetGameOutcome.win else 0),
                "loss_bettors": current_bets[BetGameOutcome.loss] + (1 if bet_for == BetGameOutcome.loss else 0),
            }

            bot.websocket_manager.emit(event="bet_update_data", widget_id=WIDGET_ID, data=payload)

            finishString = f"You have bet {points} points on this game resulting in a {'radiant' if self.spectating else ''}{bet_for.name}"

            bot.whisper(source, finishString)

    def load_commands(self, **options):
        self.commands["bet"] = Command.raw_command(
            self.command_bet,
            delay_all=0,
            delay_user=0,
            can_execute_with_whisper=True,
            description="Bet points",
            examples=[
                CommandExample(
                    None,
                    "Bet 69 points on a win",
                    chat="user:!bet win 69\n" "bot>user: You have bet 69 points on this game resulting in a win.",
                    description="Bet 69 points that the streamer will win",
                ).parse()
            ],
        )

        self.commands["openbet"] = Command.raw_command(
            self.command_open, level=420, delay_all=0, delay_user=0, description="Open bets"
        )
        self.commands["restartbet"] = Command.raw_command(
            self.command_restart, level=420, delay_all=0, delay_user=0, description="Restart bets"
        )
        self.commands["stopbet"] = Command.raw_command(
            self.command_stop_bet, level=420, delay_all=0, delay_user=0, description="Refunds and stops bets"
        )
        self.commands["closebet"] = Command.raw_command(
            self.command_close, level=420, delay_all=0, delay_user=0, description="Close bets"
        )
        self.commands["betstatus"] = Command.raw_command(
            self.command_betstatus, level=420, description="Status of bets"
        )
        self.commands["currentbets"] = Command.raw_command(self.command_stats, level=100, delay_all=0, delay_user=10)
        self.commands["currentratio"] = Command.raw_command(
            self.command_stats_ratio, level=100, delay_all=0, delay_user=10
        )

    def enable(self, bot):
        if not bot:
            return

        self.reminder_job = ScheduleManager.execute_every(200, self.reminder_bet)

    def disable(self, bot):
        if not bot:
            return

        self.reminder_job.remove()
        self.reminder_job = None
