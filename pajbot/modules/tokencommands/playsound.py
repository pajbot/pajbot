import logging

from numpy import random

import pajbot.models
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.modules import QuestModule

log = logging.getLogger(__name__)


class Samples:
    valid_samples = {
            '4head': { 'length': 0 },
            '4header': { 'length': 0 },
            '7777': { 'length': 0 },
            'aaaah': { 'length': 0 },
            'actioniscoming': { 'length': 0 },
            'amazing': { 'length': 0 },
            'asswecan': { 'length': 0 },
            'athene': { 'length': 0 },
            'attention': { 'length': 0 },
            'beatme123': { 'length': 0 },
            'behindyou': { 'length': 0 },
            'bitch': { 'length': 0 },
            'bomblobber': { 'length': 0 },
            'bondagegaywebsite': { 'length': 0 },
            'bossofthisgym': { 'length': 0 },
            'boyishgiggles': { 'length': 0 },
            'bruceuiscoming': { 'length': 0 },
            'bubble': { 'length': 0 },
            'car': { 'length': 0 },
            'celebrate': { 'length': 0 },
            'collegeboy': { 'length': 0 },
            'comeonletsgo': { 'length': 0 },
            'cumming': { 'length': 0 },
            'damnson': { 'length': 0 },
            'dayum': { 'length': 0 },
            'deadlycommandos': { 'length': 0 },
            'djkarlthedog': { 'length': 0 },
            'doitdad': { 'length': 0 },
            'doot': { 'length': 0 },
            'eatthepoopoo': { 'length': 0 },
            'embarrassing': { 'length': 0 },
            'eshrug': { 'length': 0 },
            'face': { 'length': 0 },
            'fatcock': { 'length': 0 },
            'forsenswa': { 'length': 0 },
            'fuckyou': { 'length': 0 },
            'gamba': { 'length': 0 },
            'gangingup': { 'length': 0 },
            'goodvibes': { 'length': 0 },
            'heftobemad': { 'length': 0 },
            'heyguyshowsitgoinkripparrianhere': { 'length': 0 },
            'howstrong': { 'length': 0 },
            'hyperbruh': { 'length': 0 },
            'idontdoanal': { 'length': 0 },
            'iseeyou1': { 'length': 0 },
            'iseeyou2': { 'length': 0 },
            'jabroni': { 'length': 0 },
            'jeff': { 'length': 0 },
            'jesse': { 'length': 0 },
            'knock': { 'length': 0 },
            'lashofthespanking': { 'length': 0 },
            'legendary': { 'length': 0 },
            'levelup': { 'length': 0 },
            'loan': { 'length': 0 },
            'lul': { 'length': 0 },
            'march': { 'length': 0 },
            'mistake': { 'length': 0 },
            'mysummercmonman': { 'length': 0 },
            'nani': { 'length': 0 },
            'no': { 'length': 0 },
            'nothinghere': { 'length': 0 },
            'ohbabyatriple': { 'length': 0 },
            'ohmancmonman': { 'length': 0 },
            'ohmyshoulder': { 'length': 0 },
            'oooh': { 'length': 0 },
            'oooooh': { 'length': 0 },
            'othernight': { 'length': 0 },
            'pain1': { 'length': 0 },
            'pants': { 'length': 0 },
            'pewdiepie': { 'length': 0 },
            'pleaseno': { 'length': 0 },
            'poopooiscoming': { 'length': 0 },
            'power': { 'length': 0 },
            'powerfuck': { 'length': 0 },
            'pphop': { 'length': 0 },
            'puke': { 'length': 0 },
            'pullupourpants': { 'length': 0 },
            'realtrapshit': { 'length': 0 },
            'relax': { 'length': 0 },
            'reynad': { 'length': 0 },
            'righthappy': { 'length': 0 },
            'scamazishere': { 'length': 0 },
            'shakalaka': { 'length': 0 },
            'sheeeit': { 'length': 0 },
            'sike': { 'length': 0 },
            'sixhotloads': { 'length': 0 },
            'slap': { 'length': 0 },
            'smartass': { 'length': 0 },
            'sorry': { 'length': 0 },
            'spankmoan1': { 'length': 0 },
            'specimen': { 'length': 0 },
            'spook': { 'length': 0 },
            'suction': { 'length': 0 },
            'surprise': { 'length': 0 },
            'takeit': { 'length': 0 },
            'ting1': { 'length': 0 },
            'ting2': { 'length': 0 },
            'ting3': { 'length': 0 },
            'tuckfrump': { 'length': 0 },
            'ultralul': { 'length': 0 },
            'umad': { 'length': 0 },
            'vibrate': { 'length': 0 },
            'water': { 'length': 0 },
            'weed': { 'length': 0 },
            'woah': { 'length': 0 },
            'woop': { 'length': 0 },
            'wrongdoor': { 'length': 0 },
            'wrongnumba': { 'length': 0 },
            'yeehaw': { 'length': 0 },
            'yessir': { 'length': 0 },
            'youlikechallenges': { 'length': 0 },
            'youlikethat': { 'length': 0 },
        }


class PlaySoundTokenCommandModule(BaseModule):

    ID = 'tokencommand-' + __name__.split('.')[-1]
    NAME = '!playsound'
    DESCRIPTION = 'Play a sound on stream'
    PARENT_MODULE = QuestModule
    SETTINGS = [
            ModuleSetting(
                key='point_cost',
                label='Point cost',
                type='number',
                required=True,
                placeholder='Point cost',
                default=0,
                constraints={
                    'min_value': 0,
                    'max_value': 999999,
                    }),
            ModuleSetting(
                key='token_cost',
                label='Token cost',
                type='number',
                required=True,
                placeholder='Token cost',
                default=3,
                constraints={
                    'min_value': 0,
                    'max_value': 15,
                    }),
            ModuleSetting(
                key='sample_cd',
                label='Cooldown for the same sample (seconds)',
                type='number',
                required=True,
                placeholder='',
                default=20,
                constraints={
                    'min_value': 5,
                    'max_value': 120,
                    }),
            ModuleSetting(
                key='sub_only',
                label='Subscribers only',
                type='boolean',
                required=True,
                default=True),
            ModuleSetting(
                key='global_cd',
                label='Global playsound cooldown (seconds)',
                type='number',
                required=True,
                placeholder='',
                default=2,
                constraints={
                    'min_value': 0,
                    'max_value': 600,
                    }),
            ]

    def __init__(self):
        super().__init__()
        self.valid_samples = Samples.valid_samples
        self.sample_cache = []

    def play_sound(self, **options):
        bot = options['bot']
        message = options['message']
        source = options['source']

        if message:
            sample = message.split(' ')[0].lower()

            if sample in self.sample_cache:
                bot.whisper(source.username, 'The sample {0} was played too recently. Please wait before trying to use it again'.format(sample))
                return False

            if sample == 'random':
                sample = random.choice(self.valid_samples.keys())

            if sample in self.valid_samples:
                log.debug('Played sound: {0}'.format(sample))
                payload = {'sample': sample}
                bot.websocket_manager.emit('play_sound', payload)
                if not (source.username == 'pajlada') or True:
                    self.sample_cache.append(sample)
                    bot.execute_delayed(self.settings['sample_cd'], self.sample_cache.remove, ('{0}'.format(sample), ))
                return True

        bot.whisper(source.username, 'Your sample is not valid. Check out all the valid samples here: https://pajbot.com/playsounds')
        return False

    def load_commands(self, **options):
        self.commands['#playsound'] = pajbot.models.command.Command.raw_command(
                self.play_sound,
                tokens_cost=self.settings['token_cost'],
                cost=self.settings['point_cost'],
                sub_only=self.settings['sub_only'],
                delay_all=self.settings['global_cd'],
                description='Play a sound on stream! Costs {} tokens, sub only for now.'.format(self.settings['token_cost']),
                can_execute_with_whisper=True,
                examples=[
                    pajbot.models.command.CommandExample(None, 'Play the "cumming" sample',
                        chat='user:!#playsound cumming\n'
                        'bot>user:Successfully played your sample cumming').parse(),
                    pajbot.models.command.CommandExample(None, 'Play the "fuckyou" sample',
                        chat='user:!#playsound fuckyou\n'
                        'bot>user:Successfully played your sample fuckyou').parse(),
                    ],
                )

        self.commands['#playsound'].long_description = 'Playsounds can be tried out <a href="https://pajbot.com/playsounds">here</a>'
