import datetime
import logging
import math

import Levenshtein
import requests
from apscheduler.schedulers.background import BackgroundScheduler

from pajbot.models.command import Command
from pajbot.models.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class TriviaModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Trivia'
    DESCRIPTION = 'Trivia!'
    CATEGORY = 'Game'
    SETTINGS = [
            ModuleSetting(
                key='hint_count',
                label='How many hints the user should get before the question is ruined.',
                type='number',
                required=True,
                default=2,
                constraints={
                    'min_value': 0,
                    'max_value': 4,
                    }),
            ModuleSetting(
                key='step_delay',
                label='Time between each step (step_delay*(hint_count+1) = length of each question)',
                type='number',
                required=True,
                placeholder='',
                default=10,
                constraints={
                    'min_value': 5,
                    'max_value': 45,
                    }),
            ModuleSetting(
                key='default_point_bounty',
                label='Default point bounty per right answer',
                type='number',
                required=True,
                placeholder='',
                default=0,
                constraints={
                    'min_value': 0,
                    'max_value': 50,
                    }),
            ]

    def __init__(self):
        super().__init__()

        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.job = self.scheduler.add_job(self.poll_trivia, 'interval', seconds=1)
        self.job.pause()

        self.trivia_running = False
        self.last_question = None
        self.question = None
        self.step = 0
        self.last_step = None

        self.point_bounty = 0

    def poll_trivia(self):
        if self.question is None and (self.last_question is None or datetime.datetime.now() - self.last_question >= datetime.timedelta(seconds=12)):
            url = 'http://jservice.io/api/random'
            r = requests.get(url)
            self.question = r.json()[0]
            self.question['answer'] = self.question['answer'].replace('<i>', '').replace('</i>', '').replace('\\', '').replace('(', '').replace(')', '').strip('"').strip('.')

            if len(self.question['answer']) == 0 or len(self.question['question']) <= 1:
                self.question = None
                return

            self.step = 0
            self.last_step = None

        # Is it time for the next step?
        if self.last_step is None or datetime.datetime.now() - self.last_step >= datetime.timedelta(seconds=self.settings['step_delay']):
            self.last_step = datetime.datetime.now()
            self.step += 1

            if self.step == 1:
                self.step_announce()
            elif self.step < self.settings['hint_count'] + 2:
                self.step_hint()
            else:
                self.step_end()

    def step_announce(self):
        try:
            self.bot.me('OMGScoots A new question has begun! In the category "{0[category][title]}", the question/hint/clue is "{0[question]}" OMGScoots'.format(self.question))
        except:
            self.step = 0
            self.question = None
            pass

    def step_hint(self):
        # find out what % of the answer should be revealed
        full_hint_reveal = int(math.floor(len(self.question['answer']) / 2))
        current_hint_reveal = int(math.floor(((self.step) / self.settings['hint_count']) * full_hint_reveal))
        hint_arr = []
        index = 0
        for c in self.question['answer']:
            if c == ' ':
                hint_arr.append(' ')
            else:
                if index < current_hint_reveal:
                    hint_arr.append(self.question['answer'][index])
                else:
                    hint_arr.append('_')
            index += 1
        hint_str = ''.join(hint_arr)

        self.bot.me('OpieOP Here\'s a hint, "{hint_str}" OpieOP'.format(hint_str=hint_str))

    def step_end(self):
        if self.question is not None:
            self.bot.me('MingLee No one could answer the trivia! The answer was "{}" MingLee'.format(self.question['answer']))
            self.question = None
            self.step = 0
            self.last_question = datetime.datetime.now()

    def command_start(self, **options):
        bot = options['bot']
        source = options['source']
        message = options['message']

        if self.trivia_running:
            bot.me('{}, a trivia is already running'.format(source.username_raw))
            return

        self.trivia_running = True
        self.job.resume()

        try:
            self.point_bounty = int(message)
            if self.point_bounty < 0:
                self.point_bounty = 0
            elif self.point_bounty > 50:
                self.point_bounty = 50
        except:
            self.point_bounty = self.settings['default_point_bounty']

        if self.point_bounty > 0:
            bot.me('The trivia has started! {} points for each right answer!'.format(self.point_bounty))
        else:
            bot.me('The trivia has started!')

        HandlerManager.add_handler('on_message', self.on_message)

    def command_stop(self, **options):
        bot = options['bot']
        source = options['source']

        if not self.trivia_running:
            bot.me('{}, no trivia is active right now'.format(source.username_raw))
            return

        self.job.pause()
        self.trivia_running = False
        self.step_end()

        bot.me('The trivia has been stopped.')

        HandlerManager.remove_handler('on_message', self.on_message)

    def on_message(self, source, message, emotes, whisper, urls, event):
        if message is None:
            return

        if self.question:
            right_answer = self.question['answer'].lower()
            user_answer = message.lower()
            if len(right_answer) <= 5:
                correct = right_answer == user_answer
            else:
                ratio = Levenshtein.ratio(right_answer, user_answer)
                correct = ratio >= 0.94

            if correct:
                if self.point_bounty > 0:
                    self.bot.me('{} got the answer right! The answer was {} FeelsGoodMan They get {} points! PogChamp'.format(source.username_raw, self.question['answer'], self.point_bounty))
                    source.points += self.point_bounty
                else:
                    self.bot.me('{} got the answer right! The answer was {} FeelsGoodMan'.format(source.username_raw, self.question['answer']))

                self.question = None
                self.step = 0
                self.last_question = datetime.datetime.now()

    def load_commands(self, **options):
        self.commands['trivia'] = Command.multiaction_command(
                level=100,
                delay_all=0,
                delay_user=0,
                can_execute_with_whisper=True,
                commands={
                    'start': Command.raw_command(
                        self.command_start,
                        level=500,
                        delay_all=0,
                        delay_user=10,
                        can_execute_with_whisper=True,
                        ),
                    'stop': Command.raw_command(
                        self.command_stop,
                        level=500,
                        delay_all=0,
                        delay_user=0,
                        can_execute_with_whisper=True,
                        ),
                    }
                )

    def enable(self, bot):
        self.bot = bot
