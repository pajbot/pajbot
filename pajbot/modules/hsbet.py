import datetime
import logging

import requests

from pajbot import utils
from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.managers.redis import RedisManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.command import Command
from pajbot.models.hsbet import HSBetBet
from pajbot.models.hsbet import HSBetGame
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.streamhelper import StreamHelper

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
        self.bets = {}

        redis = RedisManager.get()

        self.last_game_start = None
        self.last_game_id = None
        try:
            last_game_start_timestamp = int(
                redis.get("{streamer}:last_hsbet_game_start".format(streamer=StreamHelper.get_streamer()))
            )
            self.last_game_start = datetime.datetime.fromtimestamp(last_game_start_timestamp, tz=datetime.timezone.utc)
        except (TypeError, ValueError):
            # Issue with the int-cast
            pass
        except (OverflowError, OSError):
            # Issue with datetime.fromtimestamp
            pass

        try:
            self.last_game_id = int(
                redis.get("{streamer}:last_hsbet_game_id".format(streamer=StreamHelper.get_streamer()))
            )
        except (TypeError, ValueError):
            pass

        self.job = ScheduleManager.execute_every(15, self.poll_trackobot)
        self.job.pause()
        self.reminder_job = ScheduleManager.execute_every(1, self.reminder_bet)
        self.reminder_job.pause()

    def reminder_bet(self):
        if self.is_betting_open():
            seconds_until_bet_closes = int((self.last_game_start - utils.now()).total_seconds()) - 1
            if (seconds_until_bet_closes % 10) == 0 and seconds_until_bet_closes > 0:
                win_points, lose_points = self.get_stats()
                self.bot.me(
                    "The hearthstone betting closes in {} seconds. Current win/lose points: {}/{}".format(
                        seconds_until_bet_closes, win_points, lose_points
                    )
                )
            elif seconds_until_bet_closes == 5:
                win_points, lose_points = self.get_stats()
                self.bot.me(
                    "The hearthstone betting closes in 5 seconds... Current win/lose points: {}/{}".format(
                        win_points, lose_points
                    )
                )
            elif seconds_until_bet_closes == 0:
                win_points, lose_points = self.get_stats()
                self.bot.me(
                    "The hearthstone betting has been closed! No longer accepting bets. Closing with win/lose points: {}/{}".format(
                        win_points, lose_points
                    )
                )

    def poll_trackobot(self):
        url = "https://trackobot.com/profile/history.json?username={username}&token={api_key}".format(
            username=self.settings["trackobot_username"], api_key=self.settings["trackobot_api_key"]
        )
        r = requests.get(url)
        game_data = r.json()
        if "history" not in game_data:
            log.error("Invalid json?")
            return False

        if len(game_data["history"]) == 0:
            log.error("No games found in the history.")
            return False

        self.bot.execute_now(lambda: self.poll_trackobot_stage2(game_data))

    def poll_trackobot_stage2(self, game_data):
        latest_game = game_data["history"][0]

        if latest_game["id"] != self.last_game_id:
            # A new game has been detected
            # Reset all variables
            winners = []
            losers = []
            total_winning_points = 0
            total_losing_points = 0
            points_bet = {"win": 0, "loss": 0}
            bet_game_id = None

            # Mark down the last game's results
            with DBManager.create_session_scope() as db_session:
                bet_game = HSBetGame(latest_game["id"], latest_game["result"])
                db_session.add(bet_game)
                db_session.flush()
                bet_game_id = bet_game.id

                db_bets = {}

                for username in self.bets:
                    bet_for_win, points = self.bets[username]
                    """
                    self.bot.me('{} bet {} points on the last game to end up as a {}'.format(
                        username,
                        points,
                        'win' if bet_for_win else 'loss'))
                        """

                    user = self.bot.users.find(username, db_session=db_session)
                    if user is None:
                        continue

                    correct_bet = (latest_game["result"] == "win" and bet_for_win is True) or (
                        latest_game["result"] == "loss" and bet_for_win is False
                    )
                    points_bet["win" if bet_for_win else "loss"] += points
                    db_bets[username] = HSBetBet(bet_game_id, user.id, "win" if bet_for_win else "loss", points, 0)
                    if correct_bet:
                        winners.append((user, points))
                        total_winning_points += points
                        user.remove_debt(points)
                    else:
                        losers.append((user, points))
                        total_losing_points += points
                        user.pay_debt(points)
                        db_bets[username].profit = -points
                        self.bot.whisper(
                            user.username,
                            "You bet {} points on the wrong outcome, so you lost it all. :(".format(points),
                        )

                for obj in losers:
                    user, points = obj
                    user.save()
                    log.debug("{} lost {} points!".format(user, points))

                for obj in winners:
                    points_reward = 0

                    user, points = obj

                    if points == 0:
                        # If you didn't bet any points, you don't get a part of the cut.
                        HandlerManager.trigger("on_user_win_hs_bet", user=user, points_won=points_reward)
                        continue

                    pot_cut = points / total_winning_points
                    points_reward = int(pot_cut * total_losing_points)
                    db_bets[user.username].profit = points_reward
                    user.points += points_reward
                    user.save()
                    HandlerManager.trigger("on_user_win_hs_bet", user=user, points_won=points_reward)
                    self.bot.whisper(
                        user.username,
                        "You bet {} points on the right outcome, that rewards you with a profit of {} points! (Your bet was {:.2f}% of the total pool)".format(
                            points, points_reward, pot_cut * 100
                        ),
                    )
                    """
                    self.bot.me('{} bet {} points, and made a profit of {} points by correctly betting on the HS game!'.format(
                        user.username_raw, points, points_reward))
                        """

                for username in db_bets:
                    bet = db_bets[username]
                    db_session.add(bet)

            self.bot.me("A new game has begun! Vote with !hsbet win/lose POINTS")
            self.bets = {}
            self.last_game_id = latest_game["id"]
            self.last_game_start = utils.now() + datetime.timedelta(seconds=self.settings["time_until_bet_closes"])
            payload = {"time_left": self.settings["time_until_bet_closes"], "win": 0, "loss": 0}
            self.bot.websocket_manager.emit("hsbet_new_game", data=payload)

            # stats about the game
            ratio = 0.0
            try:
                ratio = (total_losing_points / total_winning_points) * 100.0
            except:
                pass
            self.bot.me(
                "The game ended as a {result}. {points_bet[win]} points bet on win, {points_bet[loss]} points bet on loss. Winners can expect a {ratio:.2f}% return on their bet points.".format(
                    ratio=ratio, result=latest_game["result"], points_bet=points_bet
                )
            )

            redis = RedisManager.get()
            redis.set("{streamer}:last_hsbet_game_id".format(streamer=StreamHelper.get_streamer()), self.last_game_id)
            redis.set(
                "{streamer}:last_hsbet_game_start".format(streamer=StreamHelper.get_streamer()),
                self.last_game_start.timestamp(),
            )

    def is_betting_open(self):
        if self.last_game_start is None:
            return False
        return utils.now() < self.last_game_start

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
        elif outcome in ("lose", "loss", "loser", "loose"):
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

        if points > 0:
            payload = {"win": 0, "loss": 0}
            if bet_for_win:
                payload["win"] = points
            else:
                payload["loss"] = points
            self.bot.websocket_manager.emit("hsbet_update_data", data=payload)

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
        win_bets = 0
        loss_bets = 0
        for username in self.bets:
            bet_for_win, points = self.bets[username]
            if bet_for_win:
                win_bets += points
            else:
                loss_bets += points
        log.info("win bets: {}".format(win_bets))
        log.info("loss bets: {}".format(loss_bets))
        payload = {"time_left": time_limit, "win": win_bets, "loss": loss_bets}
        self.bot.websocket_manager.emit("hsbet_new_game", data=payload)

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

    def get_stats(self):
        """ Returns how many points are bet on win and how many points
        are bet on lose """

        win_points = 0
        lose_points = 0

        for username in self.bets:
            bet_for_win, points = self.bets[username]
            if bet_for_win:
                win_points += points
            else:
                lose_points += points

        return win_points, lose_points

    def command_stats(self, **options):
        bot = options["bot"]
        source = options["source"]

        win_points, lose_points = self.get_stats()

        bot.whisper(source.username, "Current win/lose points: {}/{}".format(win_points, lose_points))

    def load_commands(self, **options):
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
            self.job.resume()
            self.reminder_job.resume()

    def disable(self, bot):
        if bot:
            self.job.pause()
            self.reminder_job.pause()
