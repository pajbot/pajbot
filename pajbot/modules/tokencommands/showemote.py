import logging

from pajbot.models.command import Command
from pajbot.modules import BaseModule
from pajbot.modules import QuestModule

log = logging.getLogger(__name__)


class ShowEmoteTokenCommandModule(BaseModule):

    ID = 'tokencommand-' + __name__.split('.')[-1]
    NAME = 'Token Command'
    DESCRIPTION = 'Show a single emote on screen for a few seconds'
    PARENT_MODULE = QuestModule

    def show_emote(self, **options):
        bot = options['bot']
        source = options['source']
        args = options['args']

        if len(args['emotes']) == 0:
            # No emotes in the given message
            bot.whisper(source.username, 'No valid emotes were found in your message.')
            return False

        first_emote = args['emotes'][0]
        payload = {'emote': first_emote}
        bot.websocket_manager.emit('new_emote', payload)
        bot.whisper(source.username, 'Successfully sent the emote {} to the stream!'.format(first_emote['code']))

    def load_commands(self, **options):
        self.commands['#showemote'] = Command.raw_command(
                self.show_emote,
                tokens_cost=1,
                description='Show an emote on stream! Costs 1 token.',
                can_execute_with_whisper=True,
                )
