import datetime
import logging
import math

from pajbot import utils
from pajbot.managers.handler import HandlerManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.command import Command
from pajbot.modules import BaseModule, ModuleSetting

import rapidfuzz
import requests

log = logging.getLogger(__name__)


class TriviaModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Trivia"
    DESCRIPTION = "Trivia!"
    CATEGORY = "Game"
    SETTINGS = [
        ModuleSetting(
            key="hint_count",
            label="How many hints the user should get before the question is ruined.",
            type="number",
            required=True,
            default=2,
            constraints={"min_value": 0, "max_value": 4},
        ),
        ModuleSetting(
            key="step_delay",
            label="Time between each step (step_delay*(hint_count+1) = length of each question)",
            type="number",
            required=True,
            placeholder="",
            default=10,
            constraints={"min_value": 5, "max_value": 45},
        ),
        ModuleSetting(
            key="default_point_bounty",
            label="Default point bounty per right answer",
            type="number",
            required=True,
            placeholder="",
            default=0,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
        ModuleSetting(
            key="question_delay",
            label="Delay between questions in seconds.",
            type="number",
            required=True,
            placeholder="",
            default=0,
            constraints={"min_value": 0, "max_value": 600},
        ),
        ModuleSetting(
            key="commands_level",
            label="Minimum level to use !trivia start/stop",
            type="number",
            required=True,
            placeholder="",
            default=500,
            constraints={"min_value": 100, "max_value": 1500},
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)

        self.job = None

        self.trivia_running = False
        self.last_question = None
        self.question = None
        self.step = 0
        self.last_step = None

        self.point_bounty = 0

    def poll_trivia(self):
        if self.question is None and (
            self.last_question is None or utils.now() - self.last_question >= datetime.timedelta(seconds=12)
        ):
            url = "http://jservice.io/api/random"
            r = requests.get(url, headers={"User-Agent": self.bot.user_agent})
            self.question = r.json()[0]
            self.question["answer"] = (
                self.question["answer"]
                .replace("<i>", "")
                .replace("</i>", "")
                .replace("\\", "")
                .replace("(", "")
                .replace(")", "")
                .strip('"')
                .strip(".")
            )

            if (
                len(self.question["answer"]) == 0
                or len(self.question["question"]) <= 1
                or "href=" in self.question["answer"]
            ):
                self.question = None
                return

            self.step = 0
            self.last_step = None

        # Is it time for the next step?
        condition = self.last_question is None or utils.now() - self.last_question >= datetime.timedelta(
            seconds=self.settings["question_delay"]
        )
        if (self.last_step is None and condition) or (
            self.last_step is not None
            and utils.now() - self.last_step >= datetime.timedelta(seconds=self.settings["step_delay"])
        ):
            self.last_step = utils.now()
            self.step += 1

            if self.step == 1:
                self.step_announce()
            elif self.step < self.settings["hint_count"] + 2:
                self.step_hint()
            else:
                self.step_end()

    def step_announce(self):
        try:
            self.bot.safe_me(
                f'KKona A new question has begun! In the category "{self.question["category"]["title"]}", the question/hint/clue is "{self.question["question"]}" KKona'
            )
        except:
            self.step = 0
            self.question = None
            pass

    def step_hint(self):
        # find out what % of the answer should be revealed
        full_hint_reveal = int(math.floor(len(self.question["answer"]) / 2))
        current_hint_reveal = int(math.floor(((self.step) / self.settings["hint_count"]) * full_hint_reveal))
        hint_arr = []
        index = 0
        for c in self.question["answer"]:
            if c == " ":
                hint_arr.append(" ")
            else:
                if index < current_hint_reveal:
                    hint_arr.append(self.question["answer"][index])
                else:
                    hint_arr.append("_")
            index += 1
        hint_str = "".join(hint_arr)

        self.bot.safe_me(f'OpieOP Here\'s a hint, "{hint_str}" OpieOP')

    def step_end(self):
        if self.question is not None:
            self.bot.safe_me(
                f'MingLee No one could answer the trivia! The answer was "{self.question["answer"]}" MingLee'
            )
            self.question = None
            self.step = 0
            self.last_question = utils.now()

    def command_start(self, bot, source, message, **rest):
        if self.trivia_running:
            bot.safe_me(f"{source}, a trivia is already running")
            return

        self.trivia_running = True
        self.job = ScheduleManager.execute_every(1, self.poll_trivia)

        try:
            self.point_bounty = int(message)
            if self.point_bounty < 0:
                self.point_bounty = 0
            elif self.point_bounty > 50:
                self.point_bounty = 50
        except:
            self.point_bounty = self.settings["default_point_bounty"]

        if self.point_bounty > 0:
            bot.safe_me(f"The trivia has started! {self.point_bounty} points for each right answer!")
        else:
            bot.safe_me("The trivia has started!")

        HandlerManager.add_handler("on_message", self.on_message)

    def command_stop(self, bot, source, **rest):
        if not self.trivia_running:
            bot.safe_me(f"{source}, no trivia is active right now")
            return

        self.job.remove()
        self.job = None
        self.trivia_running = False
        self.step_end()

        bot.safe_me("The trivia has been stopped.")

        HandlerManager.remove_handler("on_message", self.on_message)

    def on_message(self, source, message, whisper, **rest):
        if not message or whisper:
            return

        if self.question:
            right_answer = self.question["answer"].lower()
            user_answer = message.lower()
            if len(right_answer) <= 5:
                correct = right_answer == user_answer
            else:
                ratio = rapidfuzz.fuzz.ratio(right_answer, user_answer)
                correct = ratio >= 94

            if correct:
                if self.point_bounty > 0:
                    self.bot.safe_me(
                        f"{source} got the answer right! The answer was {self.question['answer']} FeelsGoodMan They get {self.point_bounty} points! PogChamp"
                    )
                    source.points += self.point_bounty
                else:
                    self.bot.safe_me(
                        f"{source} got the answer right! The answer was {self.question['answer']} FeelsGoodMan"
                    )

                self.question = None
                self.step = 0
                self.last_question = utils.now()

    def load_commands(self, **options):
        self.commands["trivia"] = Command.multiaction_command(
            level=100,
            delay_all=0,
            delay_user=0,
            can_execute_with_whisper=True,
            commands={
                "start": Command.raw_command(
                    self.command_start,
                    level=self.settings["commands_level"],
                    delay_all=0,
                    delay_user=10,
                    can_execute_with_whisper=True,
                ),
                "stop": Command.raw_command(
                    self.command_stop,
                    level=self.settings["commands_level"],
                    delay_all=0,
                    delay_user=0,
                    can_execute_with_whisper=True,
                ),
            },
        )
