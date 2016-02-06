import logging

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.modules import QuestModule
from pajbot.models.command import Command

log = logging.getLogger(__name__)

class PlaySoundTokenCommandModule(BaseModule):

    ID = 'tokencommand-' + __name__.split('.')[-1]
    NAME = 'Token Command'
    DESCRIPTION = 'Play a sound on stream'
    PARENT_MODULE = QuestModule

    def play_sound(self, **options):
        log.info('Play sound!')
        bot = options['bot']
        message = options['message']
        source = options['source']

        valid_samples = ['bossofthisgym', 'fuckyou', 'idontdoanal', 'knock', 'slap', 'cumming', 'collegeboy', 'oooh', 'suction', 'takeit', 'amazing', 'power', 'othernight', 'asswecan', 'lashofthespanking', 'nyanpass']

        if message:
            sample = message.split(' ')[0].lower()
            if sample in valid_samples:
                payload = {'sample': sample}
                bot.websocket_manager.emit('play_sound', payload)
                bot.whisper(source.username, 'Successfully played your sample {}'.format(sample))
                return True

        bot.whisper(source.username, 'Your sample is not valid.  Use one of the following as argument: {}'.format(', '.join(valid_samples)))
        return False

    def load_commands(self, **options):
        self.commands['#playsound'] = Command.raw_command(self.play_sound,
                tokens_cost=3)
