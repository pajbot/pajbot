import logging

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.modules import QuestModule
from pajbot.models.command import Command

log = logging.getLogger(__name__)

class ShowEmoteTokenCommandModule(BaseModule):

    ID = 'tokencommand-' + __name__.split('.')[-1]
    NAME = 'Token Command'
    DESCRIPTION = 'Show a single emote on screen for a few seconds'
    PARENT_MODULE = QuestModule

    def show_emote(self, **options):
        bot = options['bot']
        args = options['args']

        if len(args['emotes']) == 0:
            # No emotes in the given message
            return False

        first_emote = args['emotes'][0]
        payload = {'emote': first_emote}
        bot.websocket_manager.emit('new_emote', payload)

    def load_commands(self):
        self.commands['#showemote'] = Command.raw_command(self.show_emote,
                tokens_cost=1)
