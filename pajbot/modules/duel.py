import logging

from datetime import timedelta

import random

from pajbot import utils
from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.models.user import User
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class DuelModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Duel"
    DESCRIPTION = "Let users duel to win or lose points."
    CATEGORY = "Game"
    SETTINGS = [
        ModuleSetting(
            key="max_pot",
            label="How many points you can duel for at most",
            type="number",
            required=True,
            placeholder="",
            default=420,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
        ModuleSetting(
            key="message_won",
            label="Winner message | Available arguments: {winner}, {loser}",
            type="text",
            required=True,
            placeholder="{winner} won the duel vs {loser} PogChamp",
            default="{winner} won the duel vs {loser} PogChamp",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="message_won_points",
            label="Points message | Available arguments: {winner}, {loser}, {total_pot}, {extra_points}",
            type="text",
            required=True,
            placeholder="{winner} won the duel vs {loser} PogChamp . The pot was {total_pot}, the winner gets their bet back + {extra_points} points",
            default="{winner} won the duel vs {loser} PogChamp . The pot was {total_pot}, the winner gets their bet back + {extra_points} points",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="duel_tax",
            label="Duel tax (deduct this percent value from the win)",
            type="number",
            required=True,
            placeholder="",
            default=30,
            constraints={"min_value": 0, "max_value": 100},
        ),
        ModuleSetting(
            key="online_global_cd",
            label="Global cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=0,
            constraints={"min_value": 0, "max_value": 120},
        ),
        ModuleSetting(
            key="online_user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=5,
            constraints={"min_value": 0, "max_value": 240},
        ),
        ModuleSetting(
            key="show_on_clr", label="Show duels on the clr overlay", type="boolean", required=True, default=True
        ),
        ModuleSetting(
            key="max_duel_age",
            label="Auto-cancel duels after this many minutes",
            type="number",
            required=True,
            placeholder="",
            default=5,
            constraints={"min_value": 1, "max_value": 60},
        ),
    ]

    def load_commands(self, **options):
        self.commands["duel"] = Command.raw_command(
            self.initiate_duel,
            delay_all=self.settings["online_global_cd"],
            delay_user=self.settings["online_user_cd"],
            description="Initiate a duel with a user",
            examples=[
                CommandExample(
                    None,
                    "0-point duel",
                    chat="user:!duel Karl_Kons\n" "bot>user:You have challenged Karl_Kons for 0 points",
                    description="Duel Karl_Kons for 0 points",
                ).parse(),
                CommandExample(
                    None,
                    "69-point duel",
                    chat="user:!duel Karl_Kons 69\n" "bot>user:You have challenged Karl_Kons for 69 points",
                    description="Duel Karl_Kons for 69 points",
                ).parse(),
            ],
        )
        self.commands["cancelduel"] = Command.raw_command(
            self.cancel_duel, delay_all=0, delay_user=10, description="Cancel your duel request"
        )
        self.commands["accept"] = Command.raw_command(
            self.accept_duel, delay_all=0, delay_user=0, description="Accept a duel request"
        )
        self.commands["decline"] = Command.raw_command(
            self.decline_duel, delay_all=0, delay_user=0, description="Decline a duel request"
        )
        self.commands["deny"] = self.commands["decline"]
        self.commands["duelstatus"] = Command.raw_command(
            self.status_duel, delay_all=0, delay_user=5, description="Current duel request info"
        )
        self.commands["duelstats"] = Command.raw_command(
            self.get_duel_stats, delay_all=0, delay_user=120, description="Get your duel statistics"
        )

    def __init__(self, bot):
        super().__init__(bot)
        self.duel_requests = {}
        self.duel_request_price = {}
        self.duel_targets = {}
        self.duel_begin_time = {}

        self.gc_job = None

    def initiate_duel(self, bot, source, message, **rest):
        """
        Initiate a duel with a user.
        You can also bet points on the winner.
        By default, the maximum amount of points you can spend is 420.

        How to use: !duel USERNAME POINTS_TO_BET
        """

        if message is None:
            return False

        max_pot = self.settings["max_pot"]

        msg_split = message.split()
        input = msg_split[0]

        with DBManager.create_session_scope() as db_session:
            user = User.find_by_user_input(db_session, input)
            if user is None:
                # No user was found with this username
                return False

            duel_price = 0
            if len(msg_split) > 1:
                try:
                    duel_price = int(msg_split[1])
                    if duel_price < 0:
                        return False

                    if duel_price > max_pot:
                        duel_price = max_pot
                except ValueError:
                    pass

            if source.id in self.duel_requests:
                currently_duelling = User.find_by_id(db_session, self.duel_requests[source.id])
                if currently_duelling is None:
                    del self.duel_requests[source.id]
                    return False

                bot.whisper(
                    source,
                    f"You already have a duel request active with {currently_duelling}. Type !cancelduel to cancel your duel request.",
                )
                return False

            if user == source:
                # You cannot duel yourself
                return False

            if user.last_active is None or (utils.now() - user.last_active) > timedelta(minutes=5):
                bot.whisper(
                    source,
                    "This user has not been active in chat within the last 5 minutes. Get them to type in chat before sending another challenge",
                )
                return False

            if not user.can_afford(duel_price) or not source.can_afford(duel_price):
                bot.whisper(
                    source,
                    f"You or your target do not have more than {duel_price} points, therefore you cannot duel for that amount.",
                )
                return False

            if user.id in self.duel_targets:
                challenged_by = User.find_by_id(db_session, self.duel_requests[user.id])
                bot.whisper(
                    source,
                    f"This person is already being challenged by {challenged_by}. Ask them to answer the offer by typing !deny or !accept",
                )
                return False

            self.duel_targets[user.id] = source.id
            self.duel_requests[source.id] = user.id
            self.duel_request_price[source.id] = duel_price
            self.duel_begin_time[source.id] = utils.now()
            bot.whisper(
                user,
                f"You have been challenged to a duel by {source} for {duel_price} points. You can either !accept or !deny this challenge.",
            )
            bot.whisper(source, f"You have challenged {user} for {duel_price} points")

    def cancel_duel(self, bot, source, **rest):
        """
        Cancel any duel requests you've sent.

        How to use: !cancelduel
        """

        if source.id not in self.duel_requests:
            bot.whisper(source, "You have not sent any duel requests")
            return

        with DBManager.create_session_scope() as db_session:
            challenged = User.find_by_id(db_session, self.duel_requests[source.id])
            bot.whisper(source, f"You have cancelled the duel vs {challenged}")

            del self.duel_targets[challenged.id]
            del self.duel_request_price[source.id]
            del self.duel_begin_time[source.id]
            del self.duel_requests[source.id]

    def accept_duel(self, bot, source, **rest):
        """
        Accepts any active duel requests you've received.

        How to use: !accept
        """

        if source.id not in self.duel_targets:
            bot.whisper(source, "You are not being challenged to a duel by anyone.")
            return

        with DBManager.create_session_scope() as db_session:
            requestor = User.find_by_id(db_session, self.duel_targets[source.id])
            duel_price = self.duel_request_price[self.duel_targets[source.id]]

            if not source.can_afford(duel_price) or not requestor.can_afford(duel_price):
                bot.whisper(
                    source,
                    f"Your duel request with {requestor} was cancelled due to one of you not having enough points.",
                )
                bot.whisper(
                    requestor,
                    f"Your duel request with {source} was cancelled due to one of you not having enough points.",
                )

                del self.duel_requests[requestor.id]
                del self.duel_request_price[requestor.id]
                del self.duel_begin_time[requestor.id]
                del self.duel_targets[source.id]

                return False

            source.points -= duel_price
            requestor.points -= duel_price
            winning_pot = int(duel_price * (1.0 - self.settings["duel_tax"] / 100))
            participants = [source, requestor]
            winner = random.choice(participants)
            participants.remove(winner)
            loser = participants.pop()
            winner.points += duel_price
            winner.points += winning_pot

            # Persist duel statistics
            winner.duel_stats.won(winning_pot)
            loser.duel_stats.lost(duel_price)

            arguments = {
                "winner": winner.name,
                "loser": loser.name,
                "total_pot": duel_price,
                "extra_points": winning_pot,
            }

            if duel_price > 0:
                message = self.get_phrase("message_won_points", **arguments)
                if duel_price >= 500 and self.settings["show_on_clr"]:
                    bot.websocket_manager.emit("notification", {"message": f"{winner} won the duel vs {loser}"})
            else:
                message = self.get_phrase("message_won", **arguments)
            bot.say(message)

            del self.duel_requests[requestor.id]
            del self.duel_request_price[requestor.id]
            del self.duel_begin_time[requestor.id]
            del self.duel_targets[source.id]

            HandlerManager.trigger(
                "on_duel_complete", winner=winner, loser=loser, points_won=winning_pot, points_bet=duel_price
            )

    def decline_duel(self, bot, source, **options):
        """
        Declines any active duel requests you've received.

        How to use: !decline
        """

        if source.id not in self.duel_targets:
            bot.whisper(source, "You are not being challenged to a duel")
            return False

        with DBManager.create_session_scope() as db_session:
            requestor = User.find_by_id(db_session, self.duel_targets[source.id])

            bot.whisper(source, f"You have declined the duel vs {requestor}")
            bot.whisper(requestor, f"{source} declined the duel challenge with you.")

            del self.duel_targets[source.id]
            del self.duel_requests[requestor.id]
            del self.duel_request_price[requestor.id]
            del self.duel_begin_time[requestor.id]

    def status_duel(self, bot, source, **rest):
        """
        Whispers you the current status of your active duel requests/duel targets

        How to use: !duelstatus
        """

        with DBManager.create_session_scope() as db_session:
            msg = []
            if source.id in self.duel_requests:
                duelling = User.find_by_id(db_session, self.duel_requests[source.id])
                msg.append(f"You have a duel request for {self.duel_request_price[source.id]} points by {duelling}")

            if source.id in self.duel_targets:
                challenger = User.find_by_id(db_session, self.duel_targets[source.id])
                msg.append(
                    f"You have a pending duel request from {challenger} for {self.duel_request_price[self.duel_targets[source.id]]} points"
                )

            if len(msg) > 0:
                bot.whisper(source, ". ".join(msg))
            else:
                bot.whisper(source, "You have no duel request or duel target. Type !duel USERNAME POT to duel someone!")

    @staticmethod
    def get_duel_stats(bot, source, **rest):
        """
        Whispers the users duel winratio to the user
        """
        if source.duel_stats is None:
            bot.whisper(source, "You have no recorded duels.")
            return True

        bot.whisper(
            source,
            f"duels: {source.duel_stats.duels_total} winrate: {source.duel_stats.winrate:.2f}% streak: {source.duel_stats.current_streak} profit: {source.duel_stats.profit}",
        )

    def _cancel_expired_duels(self):
        now = utils.now()
        for source_id, started_at in self.duel_begin_time.items():
            duel_age = now - started_at
            if duel_age <= timedelta(minutes=self.settings["max_duel_age"]):
                # Duel is not too old
                continue

            with DBManager.create_session_scope() as db_session:
                source = User.find_by_id(db_session, source_id)
                challenged = User.find_by_id(db_session, self.duel_requests[source.id])

                if source is not None and challenged is not None:
                    self.bot.whisper(
                        source, f"{challenged} didn't accept your duel request in time, so the duel has been cancelled."
                    )

                del self.duel_targets[self.duel_requests[source.id]]
                del self.duel_requests[source.id]
                del self.duel_request_price[source.id]
                del self.duel_begin_time[source.id]

    def enable(self, bot):
        if not bot:
            return

        # We can't use bot.execute_every directly since we can't later cancel jobs created through bot.execute_every
        self.gc_job = ScheduleManager.execute_every(30, lambda: self.bot.execute_now(self._cancel_expired_duels))

    def disable(self, bot):
        if not bot:
            return

        self.gc_job.remove()
        self.gc_job = None
