import logging

from pajbot.modules import BaseModule
from pajbot.modules import QuestModule
from pajbot.models.command import Command

log = logging.getLogger(__name__)

class Sample:
    def __init__(self, command, href):
        self.command = command
        self.href = href

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
    ]

class PlaySoundTokenCommandModule(BaseModule):

    ID = 'tokencommand-' + __name__.split('.')[-1]
    NAME = 'Token Command'
    DESCRIPTION = 'Play a sound on stream'
    PARENT_MODULE = QuestModule

    def __init__(self):
        super().__init__()
        Samples.all_samples.sort()
        self.valid_samples = [sample.command for sample in Samples.all_samples]

    def play_sound(self, **options):
        log.info('Play sound!')
        bot = options['bot']
        message = options['message']
        source = options['source']

        if message:
            sample = message.split(' ')[0].lower()
            if sample in self.valid_samples:
                payload = {'sample': sample}
                bot.websocket_manager.emit('play_sound', payload)
                bot.whisper(source.username, 'Successfully played your sample {}'.format(sample))
                return True

        log.info(', '.join(self.valid_samples))
        bot.whisper(source.username, 'Your sample is not valid. Check out all the valid samples here: https://forsen.tv/commands/playsound')
        return False

    def load_commands(self, **options):
        self.commands['#playsound'] = Command.raw_command(
                self.play_sound,
                tokens_cost=3,
                sub_only=True,
                description='Play a sound on stream! Costs 3 tokens, sub only for now.',
                can_execute_with_whisper=True,
                )
        html_valid_samples = ''.join(['<tr><td class="command-sample">!#playsound {0.command}</td><td><button id="playId{0.command}" onclick="playing{0.command}(this)">Play</button></td><td><script>var isPlaying{0.command}=0;var snd{0.command}= new Audio("{0.href}");var texts = new Array("Play", "Stop");function playing{0.command}(elem){if(isPlaying{0.command}==0){elem.innerHTML=texts[1];snd{0.command}.play();isPlaying{0.command}=1;}else{elem.innerHTML=texts[0];snd{0.command}.pause();snd{0.command}.currentTime=0;isPlaying{0.command}= 0;}}var elem =document.getElementById("playId{0.command}"");snd{0.command}.onended=function(){isPlaying{0.command}=0;elem.innerHTML=texts[0];};</script></td><td><button onclick="snd{0.command}.pause();snd{0.command}.currentTime=0;">Stop</button></td></tr>'.format(sample) for sample in Samples.all_samples])
        self.commands['#playsound'].long_description = '<h3>Valid samples</h3><table>{}</table>'.format(html_valid_samples)
