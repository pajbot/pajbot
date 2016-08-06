import logging

from numpy import random

import pajbot.models
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.modules import QuestModule

log = logging.getLogger(__name__)


class Sample:
    def __init__(self, command, *links, new=False):
        self.command = command
        self.links = links
        self.href = links[0]
        self.new = new

    def __lt__(self, other):
        return self.command < other.command


class Samples:
    all_samples = [
            Sample('bossofthisgym', 'http://soundboard.ass-we-can.com/static/music/MarkW/Boss of this gym.mp3'),
            Sample('fuckyou', 'http://soundboard.ass-we-can.com/static/music/VanD/FUCKYOU.mp3'),
            Sample('idontdoanal', 'https://pajlada.se/files/clr/i_dont_do_anal.mp3'),
            Sample('knock', 'https://pajlada.se/files/clr/knock.mp3'),
            Sample('slap', 'https://pajlada.se/files/clr/slap.mp3'),
            Sample('cumming', 'https://pajlada.se/files/clr/cumming.mp3'),
            Sample('collegeboy', 'http://soundboard.ass-we-can.com/static/music/BillyH/Come%20on%20college%20boy.mp3'),
            Sample('oooh', 'https://pajlada.se/files/clr/oooh.mp3'),
            Sample('suction', 'https://pajlada.se/files/clr/suction.mp3'),
            Sample('takeit', 'http://soundboard.ass-we-can.com/static/music/VanD/Take%20it%20boy.mp3'),
            Sample('amazing', 'http://soundboard.ass-we-can.com/static/music/VanD/That\'s%20amazing.mp3'),
            Sample('power', 'https://pajlada.se/files/clr/power.mp3'),
            Sample('othernight', 'https://pajlada.se/files/clr/othernight.mp3'),
            Sample('asswecan', 'https://pajlada.se/files/clr/ass_we_can.mp3'),
            Sample('lashofthespanking', 'http://soundboard.ass-we-can.com/static/music/BillyH/Lash%20of%20the%20spanking.mp3'),
            Sample('nyanpass', 'https://pajlada.se/files/clr/nyanpass.mp3'),
            Sample('scamazishere', 'https://pajlada.se/files/clr/scamaz_is_here.mp3'),
            Sample('lul', 'https://pajlada.se/files/clr/LUL.mp3'),
            Sample('ohmyshoulder', 'https://pajlada.se/files/clr/ohmyshoulder.mp3'),
            Sample('tuturu', 'https://pajlada.se/files/clr/tuturu.mp3'),
            Sample('attention', 'https://pajlada.se/files/clr/attention.mp3'),
            Sample('aaaah', 'https://pajlada.se/files/clr/AAAAAAAH.mp3'),
            Sample('jesse', 'https://pajlada.se/files/clr/jesse-cook.mp3'),
            Sample('shakalaka', 'https://pajlada.se/files/clr/shakalaka.mp3'),
            Sample('loan', 'https://pajlada.se/files/clr/its_a_loan.mp3'),
            Sample('spankmoan1', 'https://pajlada.se/files/clr/spankmoan1.mp3'),
            Sample('youlikechallenges', 'https://pajlada.se/files/clr/you_like_challenges.mp3'),
            Sample('youlikethat', 'https://pajlada.se/files/clr/you_like_that.mp3'),
            Sample('pants', 'https://pajlada.se/files/clr/ripped_pants.mp3'),
            Sample('oh', 'https://pajlada.se/files/clr/oh.mp3'),
            Sample('poi', 'https://pajlada.se/files/clr/poi.mp3'),
            Sample('ayaya', 'https://pajlada.se/files/clr/ayaya.mp3'),
            Sample('car', 'https://pajlada.se/files/clr/car.mp3'),
            Sample('dayum', 'https://pajlada.se/files/clr/dayum.mp3'),
            Sample('water', 'https://pajlada.se/files/clr/water1.mp3'),
            Sample('doitdad', 'https://pajlada.se/files/clr/do_it_dad.mp3'),
            Sample('face', 'https://pajlada.se/files/clr/me_go_face.mp3'),
            Sample('sike', 'https://pajlada.se/files/clr/sike.mp3'),
            Sample('yahallo', 'https://pajlada.se/files/clr/yahallo.mp3'),
            Sample('djkarlthedog', 'https://pajlada.se/files/clr/djkarlthedog.mp3'),
            Sample('bomblobber', 'https://pajlada.se/files/clr/bomb_lobber.mp3'),
            Sample('baka', 'https://pajlada.se/files/clr/baka.mp3'),
            Sample('march', 'https://pajlada.se/files/clr/march.mp3'),
            Sample('embarrassing', 'https://pajlada.se/files/clr/embarrassing.mp3'),
            Sample('yessir', 'https://pajlada.se/files/clr/yes_sir.mp3'),
            Sample('sixhotloads', 'https://pajlada.se/files/clr/six_hot_loads.mp3'),
            Sample('wrongnumba', 'https://pajlada.se/files/clr/wrong_numba.mp3'),
            Sample('sorry', 'https://pajlada.se/files/clr/sorry.mp3'),
            Sample('relax', 'https://pajlada.se/files/clr/relax.mp3'),
            Sample('vibrate', 'https://pajlada.se/files/clr/vibrate.mp3'),

            Sample('4head', 'https://pajlada.se/files/clr/4Head.mp3'),
            Sample('akarin', 'https://pajlada.se/files/clr/akarin.mp3'),
            Sample('behindyou', 'https://pajlada.se/files/clr/behindyou.mp3'),
            Sample('bitch', 'https://pajlada.se/files/clr/bitch.mp3'),
            Sample('damnson', 'https://pajlada.se/files/clr/damnson.mp3'),
            Sample('desu', 'https://pajlada.se/files/clr/desu.mp3'),
            Sample('fatcock', 'https://pajlada.se/files/clr/fatcock.mp3'),
            Sample('gangingup', 'https://pajlada.se/files/clr/gangingup.mp3'),
            Sample('iseeyou1', 'https://pajlada.se/files/clr/iseeyou1.mp3'),
            Sample('iseeyou2', 'https://pajlada.se/files/clr/iseeyou2.mp3'),
            Sample('jeff', 'https://pajlada.se/files/clr/jeff.mp3'),
            Sample('mistake', 'https://pajlada.se/files/clr/mistake.mp3'),
            Sample('ohbabyatriple', 'https://pajlada.se/files/clr/ohbabyatriple.mp3'),
            Sample('rin', 'https://pajlada.se/files/clr/rin.mp3'),
            Sample('sheeeit', 'https://pajlada.se/files/clr/sheeeit.mp3'),
            Sample('spook', 'https://pajlada.se/files/clr/spook.mp3'),
            Sample('surprise', 'https://pajlada.se/files/clr/surprise.mp3'),
            Sample('tuckfrump', 'https://pajlada.se/files/clr/tuckfrump.mp3'),
            Sample('uguu', 'https://pajlada.se/files/clr/uguu.mp3'),
            Sample('weed', 'https://pajlada.se/files/clr/weed.mp3'),
            Sample('wrongdoor', 'https://pajlada.se/files/clr/wrongdoor.mp3'),

            Sample('ryuu', 'https://pajlada.se/files/clr/hanzo.mp3', new=True),
    ]


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
            ]

    def __init__(self):
        super().__init__()
        Samples.all_samples.sort()
        self.valid_samples = [sample.command for sample in Samples.all_samples]
        self.sample_cache = []

    def play_sound(self, **options):
        bot = options['bot']
        message = options['message']
        source = options['source']

        if message:
            sample = message.split(' ')[0].lower()

            if sample in self.sample_cache:
                return False

            if sample == 'random':
                sample = random.choice(self.valid_samples)

            if sample in self.valid_samples:
                log.debug('Played sound: {0}'.format(sample))
                payload = {'sample': sample}
                bot.websocket_manager.emit('play_sound', payload)
                bot.whisper(source.username, 'Successfully played your sample {0}'.format(sample))
                self.sample_cache.append(sample)
                bot.execute_delayed(self.settings['sample_cd'], self.sample_cache.remove, ('{0}'.format(sample), ))
                return True

        bot.whisper(source.username, 'Your sample is not valid. Check out all the valid samples here: {0}/commands/playsound'.format(bot.domain))
        return False

    def load_commands(self, **options):
        self.commands['#playsound'] = pajbot.models.command.Command.raw_command(
                self.play_sound,
                tokens_cost=self.settings['token_cost'],
                cost=self.settings['point_cost'],
                sub_only=self.settings['sub_only'],
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
        global_script = """<script>
            function playOrStopSound(elem, audio) {
                if(elem.innerHTML=="Play") {
                    elem.innerHTML="Stop";
                    audio.play();
                } else {
                    elem.innerHTML="Play";
                    audio.pause();
                    audio.currentTime=0;
                }
            }
            </script>"""
        local_script = """<script>
            var elem{0.command}=document.getElementById('btnTogglePlay{0.command}');
            var snd{0.command} = new Audio("{0.href}");
            snd{0.command}.onended=function(){{elem{0.command}.innerHTML='Play';}};
            elem{0.command}.addEventListener("click", function(){{ playOrStopSound(elem{0.command}, snd{0.command}); }});
        </script>"""
        html_valid_samples = global_script
        for sample in Samples.all_samples:
            parsed_sample = local_script.format(sample)
            html_valid_samples += ''.join(['<tr><td class="command-sample{1}">!#playsound {0.command}</td><td><button id="btnTogglePlay{0.command}">Play</button>{2}</td></tr>'.format(sample, ' new' if sample.new else '', parsed_sample)])
        self.commands['#playsound'].long_description = '<h5 style="margin-top: 20px;">Valid samples</h5><table>{}</table>'.format(html_valid_samples)
