import logging

import pajbot.models
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class ShowEmoteModule(BaseModule):
    ID = __name__.split('.')[-1]
    NAME = 'Showemote'
    DESCRIPTION = 'Show a single emote on screen for a few seconds using !#showemote'
    CATEGORY = 'Feature'
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
           default=1,
           constraints={
               'min_value': 0,
               'max_value': 15,
           }),
       ModuleSetting(
           key='sub_only',
           label='Subscribers only',
           type='boolean',
           required=True,
           default=False),
       ModuleSetting(
           key='can_whisper',
           label='Command can be whispered',
           type='boolean',
           required=True,
           default=True),
        ]

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

    def load_commands(self):
        self.commands['#showemote'] = pajbot.models.command.Command.raw_command(
            self.show_emote,
            tokens_cost=self.settings['token_cost'],
            cost=self.settings['point_cost'],
            description='Show an emote on stream! Costs 1 token.',
            sub_only=self.settings['sub_only'],
            can_execute_with_whisper=self.settings['can_whisper'],
            examples=[
                pajbot.models.command.CommandExample(None, 'Show an emote on stream.',
                                                     chat='user:!#showemote Keepo\n'
                                                          'bot>user: Successfully sent the emote Keepo to the stream!',
                                                     description='').parse(),
            ])
