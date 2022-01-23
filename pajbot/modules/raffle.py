import logging
import math
import random

from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.models.command import Command, CommandExample
from pajbot.models.user import User
from pajbot.modules import BaseModule, ModuleSetting
from pajbot.streamhelper import StreamHelper

log = logging.getLogger(__name__)


def generate_winner_list(winners):
    """Takes a list of winners, and combines them into a string."""
    return ", ".join(winner.name for winner in winners)


def format_win(points_amount):
    if points_amount >= 0:
        return f"won {points_amount}"

    return f"lost {-points_amount}"


class RaffleModule(BaseModule):

    MULTI_RAFFLE_MIN_WIN_POINTS_AMOUNT = 100
    MULTI_RAFFLE_MAX_WINNERS_RATIO = 0.26
    MULTI_RAFFLE_MAX_WINNERS_AMOUNT = 200

    ID = __name__.split(".")[-1]
    NAME = "Raffle"
    DESCRIPTION = "Users can participate in a raffle to win points."
    CATEGORY = "Game"
    SETTINGS = [
        ModuleSetting(
            key="message_start",
            label="Start message | Available arguments: {length}, {points}",
            type="text",
            required=True,
            placeholder=".me A raffle has begun for {points} points. type !join to join the raffle! The raffle will end in {length} seconds",
            default=".me A raffle has begun for {points} points. type !join to join the raffle! The raffle will end in {length} seconds",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="message_running",
            label="Running message | Available arguments: {length}, {points}",
            type="text",
            required=True,
            placeholder=".me The raffle for {points} points ends in {length} seconds! Type !join to join the raffle!",
            default=".me The raffle for {points} points ends in {length} seconds! Type !join to join the raffle!",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="message_start_multi",
            label="Start message (multi) | Available arguments: {length}, {points}",
            type="text",
            required=True,
            placeholder=".me A multi-raffle has begun for {points} points. type !join to join the raffle! The raffle will end in {length} seconds",
            default=".me A multi-raffle has begun for {points} points. type !join to join the raffle! The raffle will end in {length} seconds",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="message_running_multi",
            label="Running message (multi) | Available arguments: {length}, {points}",
            type="text",
            required=True,
            placeholder=".me The multi-raffle for {points} points ends in {length} seconds! Type !join to join the raffle!",
            default=".me The multi-raffle for {points} points ends in {length} seconds! Type !join to join the raffle!",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="single_max_points",
            label="Max points for a single raffle",
            type="number",
            required=True,
            placeholder="",
            default=3000,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
        ModuleSetting(
            key="max_length",
            label="Max length for a single raffle in seconds",
            type="number",
            required=True,
            placeholder="",
            default=120,
            constraints={"min_value": 0, "max_value": 1200},
        ),
        ModuleSetting(
            key="allow_negative_raffles", label="Allow negative raffles", type="boolean", required=True, default=True
        ),
        ModuleSetting(
            key="max_negative_points",
            label="Max negative points for a single raffle",
            type="number",
            required=True,
            placeholder="",
            default=3000,
            constraints={"min_value": 1, "max_value": 1000000},
        ),
        ModuleSetting(
            key="multi_enabled",
            label="Enable multi-raffles (!multiraffle/!mraffle)",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="multi_max_points",
            label="Max points for a multi raffle",
            type="number",
            required=True,
            placeholder="",
            default=100000,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
        ModuleSetting(
            key="multi_max_length",
            label="Max length for a multi raffle in seconds",
            type="number",
            required=True,
            placeholder="",
            default=600,
            constraints={"min_value": 0, "max_value": 1200},
        ),
        ModuleSetting(
            key="multi_allow_negative_raffles",
            label="Allow negative multi raffles",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="multi_max_negative_points",
            label="Max negative points for a multi raffle",
            type="number",
            required=True,
            placeholder="",
            default=10000,
            constraints={"min_value": 1, "max_value": 1000000},
        ),
        ModuleSetting(
            key="multi_raffle_on_sub",
            label="Start a multi raffle when someone subscribes",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="default_raffle_type",
            label="Default raffle (What raffle type !raffle should invoke)",
            type="options",
            required=True,
            default="Single Raffle",
            options=["Single Raffle", "Multi Raffle"],
        ),
        ModuleSetting(
            key="show_on_clr", label="Show raffles on the clr overlay", type="boolean", required=True, default=True
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)

        self.raffle_running = False
        self.raffle_users = set()
        self.raffle_points = 0
        self.raffle_length = 0

    def load_commands(self, **options):
        self.commands["singleraffle"] = Command.raw_command(
            self.raffle,
            delay_all=0,
            delay_user=0,
            level=500,
            description="Start a raffle for points",
            command="raffle",
            examples=[
                CommandExample(
                    None,
                    "Start a raffle for 69 points",
                    chat="user:!raffle 69\n"
                    "bot:A raffle has begun for 69 points. Type !join to join the raffle! The raffle will end in 60 seconds.",
                    description="Start a 60-second raffle for 69 points",
                ).parse(),
                CommandExample(
                    None,
                    "Start a raffle with a different length",
                    chat="user:!raffle 69 30\n"
                    "bot:A raffle has begun for 69 points. Type !join to join the raffle! The raffle will end in 30 seconds.",
                    description="Start a 30-second raffle for 69 points",
                ).parse(),
            ],
        )
        self.commands["sraffle"] = self.commands["singleraffle"]
        self.commands["join"] = Command.raw_command(
            self.join,
            delay_all=0,
            delay_user=5,
            description="Join a running raffle",
            examples=[
                CommandExample(
                    None,
                    "Join a running raffle",
                    chat="user:!join",
                    description="You don't get confirmation whether you joined the raffle or not.",
                ).parse()
            ],
        )
        if self.settings["multi_enabled"]:
            self.commands["multiraffle"] = Command.raw_command(
                self.multi_raffle,
                delay_all=0,
                delay_user=0,
                level=500,
                description="Start a multi-raffle for points",
                command="multiraffle",
                examples=[
                    CommandExample(
                        None,
                        "Start a multi-raffle for 69 points",
                        chat="user:!multiraffle 69\n"
                        "bot:A multi-raffle has begun for 69 points. Type !join to join the raffle! The raffle will end in 60 seconds.",
                        description="Start a 60-second raffle for 69 points",
                    ).parse(),
                    CommandExample(
                        None,
                        "Start a multi-raffle with a different length",
                        chat="user:!multiraffle 69 30\n"
                        "bot:A multi-raffle has begun for 69 points. Type !join to join the raffle! The raffle will end in 30 seconds.",
                        description="Start a 30-second multi-raffle for 69 points",
                    ).parse(),
                ],
            )
            self.commands["mraffle"] = self.commands["multiraffle"]

        if self.settings["default_raffle_type"] == "Multi Raffle" and self.settings["multi_enabled"]:
            self.commands["raffle"] = self.commands["multiraffle"]
        else:
            self.commands["raffle"] = self.commands["singleraffle"]

    def raffle(self, bot, source, message, **rest):
        if self.raffle_running is True:
            bot.say(f"{source}, a raffle is already running OMGScoots")
            return False

        self.raffle_users = set()
        self.raffle_running = True
        self.raffle_points = 100
        self.raffle_length = 60

        try:
            if message is not None and self.settings["allow_negative_raffles"] is True:
                self.raffle_points = int(message.split()[0])
            if message is not None and self.settings["allow_negative_raffles"] is False:
                if int(message.split()[0]) >= 0:
                    self.raffle_points = int(message.split()[0])
        except (IndexError, ValueError, TypeError):
            pass

        try:
            if message is not None:
                if int(message.split()[1]) >= 5:
                    self.raffle_length = int(message.split()[1])
        except (IndexError, ValueError, TypeError):
            pass

        if self.raffle_points >= 0:
            self.raffle_points = min(self.raffle_points, self.settings["single_max_points"])
        if self.raffle_points <= -1:
            self.raffle_points = max(self.raffle_points, -self.settings["max_negative_points"])

        self.raffle_length = min(self.raffle_length, self.settings["max_length"])

        if self.settings["show_on_clr"]:
            bot.websocket_manager.emit("notification", {"message": "A raffle has been started!"})
            bot.execute_delayed(0.75, bot.websocket_manager.emit, "notification", {"message": "Type !join to enter!"})

        arguments = {"length": self.raffle_length, "points": self.raffle_points}
        bot.say(self.get_phrase("message_start", **arguments))
        arguments = {"length": round(self.raffle_length * 0.75), "points": self.raffle_points}
        bot.execute_delayed(self.raffle_length * 0.25, bot.say, self.get_phrase("message_running", **arguments))
        arguments = {"length": round(self.raffle_length * 0.50), "points": self.raffle_points}
        bot.execute_delayed(self.raffle_length * 0.50, bot.say, self.get_phrase("message_running", **arguments))
        arguments = {"length": round(self.raffle_length * 0.25), "points": self.raffle_points}
        bot.execute_delayed(self.raffle_length * 0.75, bot.say, self.get_phrase("message_running", **arguments))

        bot.execute_delayed(self.raffle_length, self.end_raffle)

    def join(self, source, **rest):
        if not self.raffle_running:
            return False

        if source.id in self.raffle_users:
            return False

        # Added user to the raffle
        self.raffle_users.add(source.id)

    def end_raffle(self):
        if not self.raffle_running:
            return False

        self.raffle_running = False

        if len(self.raffle_users) == 0:
            self.bot.me("Wow, no one joined the raffle DansGame")
            return False

        with DBManager.create_session_scope() as db_session:
            winner_id = random.choice(list(self.raffle_users))
            winner = User.find_by_id(db_session, winner_id)
            if winner is None:
                return False

            self.raffle_users = set()

            if self.settings["show_on_clr"]:
                self.bot.websocket_manager.emit(
                    "notification", {"message": f"{winner} {format_win(self.raffle_points)} points in the raffle!"}
                )

            self.bot.me(f"The raffle has finished! {winner} {format_win(self.raffle_points)} points! PogChamp")

            winner.points += self.raffle_points

            HandlerManager.trigger("on_raffle_win", winner=winner, points=self.raffle_points)

    def multi_start_raffle(self, points, length):
        if self.raffle_running:
            return False

        self.raffle_users = set()
        self.raffle_running = True
        self.raffle_points = points
        self.raffle_length = length

        if self.raffle_points >= 0:
            self.raffle_points = min(self.raffle_points, self.settings["multi_max_points"])
        if self.raffle_points <= -1:
            self.raffle_points = max(self.raffle_points, -self.settings["multi_max_negative_points"])

        self.raffle_length = min(self.raffle_length, self.settings["multi_max_length"])

        if self.settings["show_on_clr"]:
            self.bot.websocket_manager.emit("notification", {"message": "A raffle has been started!"})
            self.bot.execute_delayed(
                0.75, self.bot.websocket_manager.emit, "notification", {"message": "Type !join to enter!"}
            )

        arguments = {"length": self.raffle_length, "points": self.raffle_points}
        self.bot.say(self.get_phrase("message_start_multi", **arguments))
        arguments = {"length": round(self.raffle_length * 0.75), "points": self.raffle_points}
        self.bot.execute_delayed(
            self.raffle_length * 0.25, self.bot.say, self.get_phrase("message_running_multi", **arguments)
        )
        arguments = {"length": round(self.raffle_length * 0.50), "points": self.raffle_points}
        self.bot.execute_delayed(
            self.raffle_length * 0.50, self.bot.say, self.get_phrase("message_running_multi", **arguments)
        )
        arguments = {"length": round(self.raffle_length * 0.25), "points": self.raffle_points}
        self.bot.execute_delayed(
            self.raffle_length * 0.75, self.bot.say, self.get_phrase("message_running_multi", **arguments)
        )

        self.bot.execute_delayed(self.raffle_length, self.multi_end_raffle)

    def multi_raffle(self, bot, source, message, **rest):
        if self.raffle_running is True:
            bot.say(f"{source}, a raffle is already running OMGScoots")
            return False

        points = 100
        try:
            if message is not None and self.settings["multi_allow_negative_raffles"] is True:
                points = int(message.split()[0])
            if message is not None and self.settings["multi_allow_negative_raffles"] is False:
                if int(message.split()[0]) >= 0:
                    points = int(message.split()[0])
        except (IndexError, ValueError, TypeError):
            pass

        length = 60
        try:
            if message is not None:
                if int(message.split()[1]) >= 5:
                    length = int(message.split()[1])
        except (IndexError, ValueError, TypeError):
            pass

        self.multi_start_raffle(points, length)

    def multi_end_raffle(self):
        if not self.raffle_running:
            return False

        self.raffle_running = False

        if len(self.raffle_users) == 0:
            self.bot.me("Wow, no one joined the raffle DansGame")
            return False

        num_participants = len(self.raffle_users)

        # start out with the theoretical maximum: everybody wins
        num_winners = num_participants

        # we want to impose three limits on the winner picking:
        # - a winner should get 100 points at minimum,
        num_winners = min(num_winners, math.floor(abs(self.raffle_points) / self.MULTI_RAFFLE_MIN_WIN_POINTS_AMOUNT))

        # - winner percentage should not be higher than 26%,
        num_winners = min(num_winners, math.floor(num_participants * self.MULTI_RAFFLE_MAX_WINNERS_RATIO))

        # - and we don't want to have more than 200 winners.
        num_winners = min(num_winners, self.MULTI_RAFFLE_MAX_WINNERS_AMOUNT)

        # we at least want one person to win (some of these restrictions might calculate a maximum of 0...)
        num_winners = max(num_winners, 1)

        # now we can figure out how much each participant should win
        points_per_user = int(round(self.raffle_points / num_winners))

        # and we can pick the winners!
        winner_ids = random.sample(self.raffle_users, num_winners)
        with DBManager.create_session_scope() as db_session:
            winners = db_session.query(User).filter(User.id.in_(winner_ids)).all()

            # reset
            self.raffle_users = set()

            if num_winners == 1:
                self.bot.me(f"The multi-raffle has finished! 1 user {format_win(points_per_user)} points! PogChamp")
            else:
                self.bot.me(
                    f"The multi-raffle has finished! {num_winners} users {format_win(points_per_user)} points each! PogChamp"
                )

            winners_arr = []
            for winner in winners:
                winner.points += points_per_user
                winners_arr.append(winner)

                winners_str = generate_winner_list(winners_arr)
                if len(winners_str) > 300:
                    if len(winners_arr) == 1:
                        self.bot.me(f"{winners_str} {format_win(points_per_user)} points!")
                    else:
                        self.bot.me(f"{winners_str} {format_win(points_per_user)} points each!")
                    winners_arr = []

            if len(winners_arr) > 0:
                winners_str = generate_winner_list(winners_arr)
                if len(winners_arr) == 1:
                    self.bot.me(f"{winners_str} {format_win(points_per_user)} points!")
                else:
                    self.bot.me(f"{winners_str} {format_win(points_per_user)} points each!")

            HandlerManager.trigger("on_multiraffle_win", winners=winners, points_per_user=points_per_user)

    def on_user_sub(self, **rest):
        if self.settings["multi_raffle_on_sub"] is False:
            return

        MAX_REWARD = 10000

        points = StreamHelper.get_viewers() * 5
        if points == 0:
            points = 100
        length = 30

        points = min(points, MAX_REWARD)

        self.multi_start_raffle(points, length)

    def on_user_resub(self, num_months, **rest):
        if self.settings["multi_raffle_on_sub"] is False:
            return

        MAX_REWARD = 10000

        points = StreamHelper.get_viewers() * 5
        if points == 0:
            points = 100
        length = 30

        points = min(points, MAX_REWARD)

        points += (num_months - 1) * 500

        self.multi_start_raffle(points, length)

    def enable(self, bot):
        HandlerManager.add_handler("on_user_sub", self.on_user_sub)
        HandlerManager.add_handler("on_user_resub", self.on_user_resub)

    def disable(self, bot):
        HandlerManager.remove_handler("on_user_sub", self.on_user_sub)
        HandlerManager.remove_handler("on_user_resub", self.on_user_resub)
