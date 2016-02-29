import logging

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.models.command import Command, CommandExample

from numpy import random

log = logging.getLogger(__name__)

class EightBallModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = '8-ball'
    DESCRIPTION = 'Gives users access to the !8ball command!'
    CATEGORY = 'Game'
    SETTINGS = [
            ModuleSetting(
                key='online_global_cd',
                label='Global cooldown (seconds)',
                type='number',
                required=True,
                placeholder='',
                default=4,
                constraints={
                    'min_value': 0,
                    'max_value': 120,
                    }),
            ModuleSetting(
                key='online_user_cd',
                label='Per-user cooldown (seconds)',
                type='number',
                required=True,
                placeholder='',
                default=60,
                constraints={
                    'min_value': 0,
                    'max_value': 240,
                    }),
            ]

    def __init__(self):
        super().__init__()
        self.phrases = [
                '69% for sure',
                'are you kidding?!',
                'ask again',
                'better not tell you now',
                'definitely... not',
                'don\'t bet on it',
                'don\'t count on it',
                'doubtful',
                'for sure',
                'forget about it',
                'h    ah!',
                'hells no.',
                'if the Twitch gods grant it',
                'in due time',
                'indubitably!',
                'it is certain',
                'it is so',
                'leaning towards no',
                'look deep in your heart and you will see the answer',
                'most definitely',
                'm    ost likely',
                'my sources say yes',
                'never',
                'no wais',
                'no way!',
                'no.',
                'of course!',
                'outlook good',
                'outlook not so good',
                'perhaps',
                'please.',
                'that\'s a tough one',
                'that\'s like totally a yes. Duh!',
                '    the answer might not be not no',
                'the answer to that isn\'t pretty',
                'the heavens point to yes',
                'who knows?',
                'without a doubt',
                'yesterday it would\'ve been a yes, but today it\'s a yep',
                'you will have to     wait',
                'Signs point to yes.',
                'Yes.',
                'Reply hazy, try again.',
                'Without a doubt.',
                'My sources say no.',
                'As I see it, yes.',
                'You may rely on it.',
                'Concentrate and ask again.',
                'Outlook not so good.',
                'It is decidedly so.',
                'Better not tell you now.',
                'Very doubtful.',
                'Yes - definitely.',
                'It is certain.',
                'Cannot predict now.',
                'Most likely.',
                'Ask again later.',
                'My reply is no.',
                'Outlook good.',
                'Don\'t count on it.',
                ]

    def eightball_command(self, **options):
        source = options['source']
        bot = options['bot']
        message = options['message']

        if message and len(message) > 0:
            phrase = random.choice(self.phrases)
            bot.me('{source.username_raw}, the 8-ball says... {phrase}'.format(source=source, phrase=phrase))

    def load_commands(self, **options):
        self.commands['8ball'] = Command.raw_command(self.eightball_command,
                delay_all=self.settings['online_global_cd'],
                delay_user=self.settings['online_user_cd'],
                description='Need help with a decision? Use the !8ball command!',
                examples=[
                    CommandExample(None, '!8ball',
                        chat='user:!8ball Should I listen to gachimuchi?\n'
                        'bot:pajlada, the 8-ball says... Of course you should!',
                        description='Ask the 8ball an important question').parse(),
                    ],
                )
