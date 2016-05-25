import logging

from numpy import random

import pajbot.models
from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class BingoModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Bingo Games'
    DESCRIPTION = 'Chat Bingo Game for Twitch and BTTV Emotes'
    ENABLED_DEFAULT = False
    CATEGORY = 'Game'
    SETTINGS = [
            ModuleSetting(
                key='max_points',
                label='Max points for a bingo',
                type='number',
                required=True,
                placeholder='',
                default=3000,
                constraints={
                    'min_value': 0,
                    'max_value': 35000,
                    }),
            ModuleSetting(
                key='allow_negative_bingo',
                label='Allow negative bingo',
                type='boolean',
                required=True,
                default=True),
            ModuleSetting(
                key='max_negative_points',
                label='Max negative points for a bingo',
                type='number',
                required=True,
                placeholder='',
                default=1500,
                constraints={
                    'min_value': 1,
                    'max_value': 35000,
                    })
            ]

    def __init__(self):
        super().__init__()
        self.bot = None

        self.bingo_running = False
        self.bingo_bttv_twitch_running = False

    def load_commands(self, **options):
        self.commands['bingo'] = pajbot.models.command.Command.multiaction_command(
                level=500,
                default=None,
                command='bingo',
                commands={
                    'emotes': pajbot.models.command.Command.raw_command(self.bingo_emotes,
                        level=500,
                        delay_all=15,
                        delay_user=15,
                        description='Start an emote bingo with BTTV and TWITCH global emotes',
                        examples=[
                            pajbot.models.command.CommandExample(None, 'Emote bingo for 100 points',
                                chat='user:!bingo emotes\n'
                                'bot: A bingo has started! Guess the right target to win 100 points! Only one target per message! ',
                                description='').parse(),
                            pajbot.models.command.CommandExample(None, 'Emote bingo for 222 points',
                                chat='user:!bingo emotes 222\n'
                                'bot: A bingo has started! Guess the right target to win 222 points! Only one target per message! ',
                                description='').parse(),
                            ]),
                    'bttv': pajbot.models.command.Command.raw_command(self.bingo_bttv,
                        level=500,
                        delay_all=15,
                        delay_user=15,
                        description='Start an emote bingo with BTTV global emotes',
                        examples=[
                            pajbot.models.command.CommandExample(None, 'Emote bingo for 100 points',
                                chat='user:!bingo bttv\n'
                                'bot: A bingo has started! Guess the right target to win 100 points! Only one target per message! Use BTTV global emotes. ',
                                description='').parse(),
                            pajbot.models.command.CommandExample(None, 'Emote bingo for 222 points',
                                chat='user:!bingo bttv 222\n'
                                'bot: A bingo has started! Guess the right target to win 222 points! Only one target per message! Use BTTV global emotes. ',
                                description='').parse(),
                            ]),
                    'twitch': pajbot.models.command.Command.raw_command(self.bingo_twitch,
                        level=500,
                        delay_all=15,
                        delay_user=15,
                        description='Start an emote bingo with TWITCH global emotes',
                        examples=[
                            pajbot.models.command.CommandExample(None, 'Emote bingo for 100 points',
                                chat='user:!bingo twitch\n'
                                'bot: A bingo has started! Guess the right target to win 100 points! Only one target per message! Use TWITCH global emotes. ',
                                description='').parse(),
                            pajbot.models.command.CommandExample(None, 'Emote bingo for 222 points',
                                chat='user:!bingo twitch 222\n'
                                'bot: A bingo has started! Guess the right target to win 222 points! Only one target per message! Use TWITCH global emotes. ',
                                description='').parse(),
                            ]),
                    'cancel': pajbot.models.command.Command.raw_command(self.bingo_cancel,
                        level=500,
                        delay_all=15,
                        delay_user=15,
                        description='Cancel a running bingo',
                        examples=[
                            pajbot.models.command.CommandExample(None, 'Cancel a bingo',
                                chat='user:!bingo cancel\n'
                                'bot: Bingo cancelled by pajlada FeelsBadMan',
                                description='').parse(),
                            ]),
                    'help': pajbot.models.command.Command.raw_command(self.bingo_help_random,
                        level=500,
                        delay_all=15,
                        delay_user=15,
                        description='The bot will help the chat with a random letter from the bingo target',
                        examples=[
                            pajbot.models.command.CommandExample(None, 'Get a random letter from the bingo target',
                                chat='user:!bingo help\n'
                                'bot: A bingo for 100 points is still running. You should maybe use a a a a a for the target',
                                description='').parse(),
                            ]),
                    'cheat': pajbot.models.command.Command.raw_command(self.bingo_help_first,
                        level=500,
                        delay_all=15,
                        delay_user=15,
                        description='The bot will help the chat with the first letter from the bingo target',
                        examples=[
                            pajbot.models.command.CommandExample(None, 'Get the first letter from the bingo target',
                                chat='user:!bingo cheat\n'
                                'bot: A bingo for 100 points is still running. You should use W W W W W as the first letter for the target',
                                description='').parse(),
                            ]),
                    })

    def set_bingo_target(self, target, bingo_points_win):
        self.bingo_target = target
        self.bingo_running = True
        self.bingo_points = bingo_points_win
        log.debug('Bingo target set: {0} for {1} points'.format(target, bingo_points_win))

    def set_bingo_target_bttv(self, target_bttv, bingo_points_win):
        self.bingo_target = target_bttv
        self.bingo_running = True
        self.bingo_points = bingo_points_win
        log.debug('Bingo Bttv target set: {0} for {1} points'.format(target_bttv, bingo_points_win))

    def bingo_emotes(self, bot, source, message, event, args):
        """ Twitch and BTTV emotes """
        if hasattr(self, 'bingo_running') and self.bingo_running is True:
            bot.me('{0}, a bingo is already running OMGScoots'.format(source.username_raw))
            return False

        self.bingo_bttv_twitch_running = True
        start_random_emote_bingo = random.choice(['1', '2'])
        if start_random_emote_bingo == '1':
            return self.bingo_twitch(bot, source, message, event, args)
        elif start_random_emote_bingo == '2':
            return self.bingo_bttv(bot, source, message, event, args)

    def bingo_bttv(self, bot, source, message, event, args):
        """ BTTV emotes """
        if hasattr(self, 'bingo_running') and self.bingo_running is True:
            bot.me('{0}, a bingo is already running OMGScoots'.format(source.username_raw))
            return False

        bingo_points_win = 100

        try:
            if message is not None and self.settings['allow_negative_bingo'] is True:
                bingo_points_win = int(message.split()[0])
            if message is not None and self.settings['allow_negative_bingo'] is False:
                if int(message.split()[0]) >= 0:
                    bingo_points_win = int(message.split()[0])
        except (IndexError, TypeError, ValueError):
            pass

        if bingo_points_win >= 0:
            bingo_points_win = min(bingo_points_win, self.settings['max_points'])
        if bingo_points_win <= -1:
            bingo_points_win = max(bingo_points_win, -self.settings['max_negative_points'])

        self.emotes_bttv = bot.emotes.get_global_bttv_emotes()

        target_bttv = random.choice(self.emotes_bttv)
        self.set_bingo_target_bttv(target_bttv, bingo_points_win)
        if hasattr(self, 'bingo_bttv_twitch_running') and self.bingo_bttv_twitch_running is True:
            bot.me('A bingo has started! Guess the right target to win {0} points! Only one target per message! Use BTTV and TWITCH global emotes.'.format(bingo_points_win))
            bot.websocket_manager.emit('notification', {'message': 'A bingo has started!'})
            bot.execute_delayed(0.75, bot.websocket_manager.emit, ('notification', {'message': 'Guess the target, win the prize!'}))
            return True
        else:
            bot.me('A bingo has started! Guess the right target to win {0} points! Only one target per message! Use BTTV global emotes.'.format(bingo_points_win))
            bot.websocket_manager.emit('notification', {'message': 'A bingo has started!'})
            bot.execute_delayed(0.75, bot.websocket_manager.emit, ('notification', {'message': 'Guess the target, win the prize!'}))
            return False

    def bingo_twitch(self, bot, source, message, event, args):
        """ Twitch emotes """
        if hasattr(self, 'bingo_running') and self.bingo_running is True:
            bot.me('{0}, a bingo is already running OMGScoots'.format(source.username_raw))
            return False

        bingo_points_win = 100

        try:
            if message is not None and self.settings['allow_negative_bingo'] is True:
                bingo_points_win = int(message.split()[0])
            if message is not None and self.settings['allow_negative_bingo'] is False:
                if int(message.split()[0]) >= 0:
                    bingo_points_win = int(message.split()[0])
        except (IndexError, TypeError, ValueError):
            pass

        if bingo_points_win >= 0:
            bingo_points_win = min(bingo_points_win, self.settings['max_points'])
        if bingo_points_win <= -1:
            bingo_points_win = max(bingo_points_win, -self.settings['max_negative_points'])

        self.emotes = bot.emotes.get_global_emotes()

        target = random.choice(self.emotes)
        self.set_bingo_target(target, bingo_points_win)
        if hasattr(self, 'bingo_bttv_twitch_running') and self.bingo_bttv_twitch_running is True:
            bot.me('A bingo has started! Guess the right target to win {0} points! Only one target per message! Use BTTV and TWITCH global emotes.'.format(bingo_points_win))
            bot.websocket_manager.emit('notification', {'message': 'A bingo has started!'})
            bot.execute_delayed(0.75, bot.websocket_manager.emit, ('notification', {'message': 'Guess the target, win the prize!'}))
            return True
        else:
            bot.me('A bingo has started! Guess the right target to win {0} points! Only one target per message! Use TWITCH global emotes.'.format(bingo_points_win))
            bot.websocket_manager.emit('notification', {'message': 'A bingo has started!'})
            bot.execute_delayed(0.75, bot.websocket_manager.emit, ('notification', {'message': 'Guess the target, win the prize!'}))
            return False

    def bingo_cancel(self, bot, source, message, event, args):
        """ cancel a bingo """
        if hasattr(self, 'bingo_running') and self.bingo_running is True:
            bot.me('Bingo cancelled by {0} FeelsBadMan'.format(source.username_raw))
            log.debug('Bingo cancelled by {0}'.format(source.username_raw))
            self.bingo_running = False
            self.bingo_bttv_twitch_running = False
            return True
        else:
            bot.me('{0}, no bingo is currently running FailFish'.format(source.username_raw))
            return False

    def bingo_help_random(self, bot, source, message, event, args):
        """ Random letter of the target """
        if hasattr(self, 'bingo_running') and self.bingo_running is True:
            target_split_random = random.choice(list(self.bingo_target.lower()))
            bot.me('A bingo for {0} points is still running. You should maybe use the letter {1} {1} {1} {1} {1} for the target'.format(self.bingo_points, target_split_random))
            log.debug('Bingo help: {0}'.format(target_split_random))
            return True
        else:
            bot.me('{0}, no bingo is currently running FailFish'.format(source.username_raw))
            return False

    def bingo_help_first(self, bot, source, message, event, args):
        """ First letter of the target """
        if hasattr(self, 'bingo_running') and self.bingo_running is True:
            target_first_letter = ' '.join(list(self.bingo_target)[:1])
            bot.me('A bingo for {0} points is still running. You should use {1} {1} {1} {1} {1} as the first letter for the target'.format(self.bingo_points, target_first_letter))
            log.debug('Bingo help: {0}'.format(target_first_letter))
            return True
        else:
            bot.me('{0}, no bingo is currently running FailFish'.format(source.username_raw))
            return False

    def on_message(self, source, msg_raw, message_emotes, whisper, urls, event):
        if len(message_emotes) > 0:
            if hasattr(self, 'bingo_running') and self.bingo_running is True:
                if len(message_emotes) == 1 and len(msg_raw.split(' ')) == 1:
                    if message_emotes[0]['code'] == self.bingo_target:
                        HandlerManager.trigger('on_bingo_win', source, self.bingo_points, self.bingo_target)
                        self.bingo_running = False
                        self.bingo_bttv_twitch_running = False
                        self.bot.me('{0} won the bingo! {1} was the target. Congrats, {2} points to you PogChamp'.format(source.username_raw, self.bingo_target, self.bingo_points))
                        source.points += self.bingo_points
                        log.info('{0} won the bingo for {1} points!'.format(source.username_raw, self.bingo_points))

    def enable(self, bot):
        HandlerManager.add_handler('on_message', self.on_message)

        self.bot = bot

    def disable(self, bot):
        HandlerManager.remove_handler('on_message', self.on_message)
