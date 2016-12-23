import logging
import random

import pajbot.models
from pajbot.managers.handler import HandlerManager
from pajbot.managers.redis import RedisManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.streamhelper import StreamHelper
from pajbot.utils import find

log = logging.getLogger(__name__)


class QuestModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Quest system'
    DESCRIPTION = 'Give users a single quest at the start of each day'
    CATEGORY = 'Game'
    SETTINGS = [
            ModuleSetting(
                key='action_currentquest',
                label='MessageAction for !currentquest',
                type='options',
                required=True,
                default='say',
                options=[
                    'say',
                    'whisper',
                    'me',
                    'reply',
                    ]),
            ModuleSetting(
                key='action_tokens',
                label='MessageAction for !tokens',
                type='options',
                required=True,
                default='whisper',
                options=[
                    'say',
                    'whisper',
                    'me',
                    'reply',
                    ]),
            ModuleSetting(
                key='reward_type',
                label='Reward type',
                type='options',
                required=True,
                default='tokens',
                options=[
                    'tokens',
                    'points',
                    ]),
            ModuleSetting(
                key='reward_amount',
                label='Reward amount',
                type='number',
                required=True,
                default=5,
                ),
            ModuleSetting(
                key='max_tokens',
                label='Max tokens',
                type='number',
                required=True,
                default=15,
                constraints={
                    'min_value': 1,
                    'max_value': 5000,
                    }),
            ]

    def __init__(self):
        super().__init__()
        self.current_quest = None

    def my_progress(self, **options):
        bot = options['bot']
        source = options['source']
        if self.current_quest is not None:
            quest_progress = self.current_quest.get_user_progress(source.username)
            quest_limit = self.current_quest.get_limit()

            if quest_limit is not None and quest_progress >= quest_limit:
                bot.whisper(source.username, 'You have completed todays quest!'.format(quest_progress))
            elif quest_progress is not False:
                bot.whisper(source.username, 'Your current quest progress is {}'.format(quest_progress))
            else:
                bot.whisper(source.username, 'You have no progress on the current quest.')
        else:
            bot.say('{}, There is no quest active right now.'.format(source.username_raw))

    def get_current_quest(self, **options):
        bot = options['bot']
        event = options['event']
        source = options['source']

        if self.current_quest is not None:
            message_quest = '{0}, the current quest active is {1}.'.format(source.username_raw, self.current_quest.get_objective())
        else:
            message_quest = '{0}, there is no quest active right now.'.format(source.username_raw)

        if self.settings['action_currentquest'] == 'say':
            bot.say(message_quest)
        elif self.settings['action_currentquest'] == 'whisper':
            bot.whisper(source.username, message_quest)
        elif self.settings['action_currentquest'] == 'me':
            bot.me(message_quest)
        elif self.settings['action_currentquest'] == 'reply':
            if event.type in ['action', 'pubmsg']:
                bot.say(message_quest)
            elif event.type == 'whisper':
                bot.whisper(source.username, message_quest)

    def get_user_tokens(self, **options):
        bot = options['bot']
        event = options['event']
        source = options['source']

        message_tokens = '{0}, you have {1} tokens.'.format(source.username_raw, source.tokens)

        if self.settings['action_tokens'] == 'say':
            bot.say(message_tokens)
        elif self.settings['action_tokens'] == 'whisper':
            bot.whisper(source.username, message_tokens)
        elif self.settings['action_tokens'] == 'me':
            bot.me(message_tokens)
        elif self.settings['action_tokens'] == 'reply':
            if event.type in ['action', 'pubmsg']:
                bot.say(message_tokens)
            elif event.type == 'whisper':
                bot.whisper(source.username, message_tokens)

    def load_commands(self, **options):
        self.commands['myprogress'] = pajbot.models.command.Command.raw_command(
                self.my_progress,
                can_execute_with_whisper=True,
                delay_all=0,
                delay_user=10,
                )
        self.commands['currentquest'] = pajbot.models.command.Command.raw_command(
                self.get_current_quest,
                can_execute_with_whisper=True,
                delay_all=2,
                delay_user=10,
                )
        self.commands['tokens'] = pajbot.models.command.Command.raw_command(
                self.get_user_tokens,
                can_execute_with_whisper=True,
                delay_all=0,
                delay_user=10,
                )

        self.commands['quest'] = self.commands['currentquest']

    def on_stream_start(self):
        available_quests = list(filter(lambda m: m.ID.startswith('quest-'), self.submodules))
        if len(available_quests) == 0:
            log.error('No quests enabled.')
            return False

        self.current_quest = random.choice(available_quests)
        self.current_quest.quest_module = self
        self.current_quest.start_quest()

        redis = RedisManager.get()

        redis.set(self.current_quest_key, self.current_quest.ID)

        self.bot.say('Stream started, new quest has been chosen!')
        self.bot.say('Current quest objective: {}'.format(self.current_quest.get_objective()))

    def on_stream_stop(self):
        if self.current_quest is None:
            log.info('No quest active on stream stop.')
            return False

        self.current_quest.stop_quest()
        self.current_quest = None
        self.bot.say('Stream ended, quest has been reset.')

        redis = RedisManager.get()

        # Remove any mentions of the current quest
        redis.delete(self.current_quest_key)

        last_stream_id = StreamHelper.get_last_stream_id()
        if last_stream_id is False:
            log.error('No last stream ID found.')
            # No last stream ID found. why?
            return False

    def on_loaded(self):
        if self.bot:
            self.current_quest_key = '{streamer}:current_quest'.format(streamer=self.bot.streamer)

    def on_managers_loaded(self):
        if self.current_quest is None:
            redis = RedisManager.get()

            current_quest_id = redis.get(self.current_quest_key)

            log.info('Try to load submodule with ID {}'.format(current_quest_id))

            if current_quest_id is not None:
                current_quest_id = current_quest_id
                quest = find(lambda m: m.ID == current_quest_id, self.submodules)

                if quest is not None:
                    log.info('Resumed quest {}'.format(quest.get_objective()))
                    self.current_quest = quest
                    self.current_quest.quest_module = self
                    self.current_quest.start_quest()
                else:
                    log.info('No quest with id {} found in submodules ({})'.format(current_quest_id, self.submodules))

    def enable(self, bot):
        HandlerManager.add_handler('on_stream_start', self.on_stream_start)
        HandlerManager.add_handler('on_stream_stop', self.on_stream_stop)
        HandlerManager.add_handler('on_managers_loaded', self.on_managers_loaded)

        self.bot = bot

    def disable(self, bot):
        HandlerManager.remove_handler('on_stream_start', self.on_stream_start)
        HandlerManager.remove_handler('on_stream_stop', self.on_stream_stop)
        HandlerManager.remove_handler('on_managers_loaded', self.on_managers_loaded)
