import logging

from pajbot.modules import BaseModule

log = logging.getLogger(__name__)

class ChattersModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Chatters'
    DESCRIPTION = 'Refreshes chatters'
    ENABLED_DEFAULT = True
    CATEGORY = 'Internal'
    HIDDEN = True
    SETTINGS = []

    def __init__(self):
        super().__init__()
        self.update_chatters_interval = 5
        self.initialized = False

    def update_chatters_stage1(self):
        chatters = self.bot.twitchapi.get_chatters(self.bot.streamer)
        if len(chatters) > 0:
            self.bot.mainthread_queue.add(self.update_chatters_stage2, args=[chatters])

    def update_chatters_stage2(self, chatters):
        points = 1 if self.bot.is_online else 0

        log.debug('Updating {0} chatters'.format(len(chatters)))

        self.bot.stream_manager.update_chatters(chatters, self.update_chatters_interval)

        u_chatters = self.bot.users.bulk_load(chatters)

        for user in u_chatters:
            if self.bot.is_online:
                user.minutes_in_chat_online += self.update_chatters_interval
            else:
                user.minutes_in_chat_offline += self.update_chatters_interval
            num_points = points
            if user.subscriber:
                num_points *= 5
            if self.bot.streamer == 'forsenlol' and 'trump_sub' in user.tags:
                num_points *= 0.5
            user.touch(num_points)

    def enable(self, bot):
        """
        Update chatters every `update_chatters_interval' minutes.
        By default, this is set to run every 5 minutes.
        """
        self.bot = bot

        if bot:
            if not self.initialized:
                self.bot.execute_every(self.update_chatters_interval * 60,
                                   self.bot.action_queue.add,
                                   (self.update_chatters_stage1, ))
                self.initialized = True
            else:
                self.error('XXXXXXXXXX THIS SHOULD NOT HAPPEN')
                self.error('XXXXXXXXXX THIS SHOULD NOT HAPPEN')
                self.error('XXXXXXXXXX THIS SHOULD NOT HAPPEN')
                self.error('XXXXXXXXXX THIS SHOULD NOT HAPPEN')
                self.error('XXXXXXXXXX THIS SHOULD NOT HAPPEN')
                self.error('XXXXXXXXXX THIS SHOULD NOT HAPPEN')
