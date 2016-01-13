import logging
import re

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.models.command import Command

log = logging.getLogger(__name__)

class PyramidModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Pyramid'
    DESCRIPTION = 'Congratulates people who build successfully pyramids in twitch chat'
    SETTINGS = [
            # TODO: have settings for the phrases?
                ]

    def __init__(self):
        super().__init__()
        self.bot = None

        self.data = []
        self.going_down = False
        self.regex = re.compile(' +')

    def on_pubmsg(self, source, message):
        try:
            msg_parts = message.split(' ')
            if len(self.data) > 0:
                cur_len = len(msg_parts)
                last_len = len(self.data[-1])
                pyramid_thing = self.data[-1][0]
                len_diff = cur_len - last_len
                if abs(len_diff) == 1:
                    good = True

                    # Make sure the pyramid consists of the same item over and over again
                    for x in msg_parts:
                        if not x == pyramid_thing:
                            good = False
                            break

                    if good:
                        self.data.append(msg_parts)
                        if len_diff > 0:
                            if self.going_down:
                                self.data = []
                                self.going_down = False
                        elif len_diff < 0:
                            self.going_down = True
                            if cur_len == 1:
                                # A pyramid was finished
                                peak_length = 0
                                for x in self.data:
                                    if len(x) > peak_length:
                                        peak_length = len(x)

                                response = 'PogChamp'
                                if peak_length > 2:
                                    if peak_length < 5:
                                        response = 'That\'s pretty neat KKona //'
                                    elif peak_length < 7:
                                        response = 'Good job!!! PogChamp //'
                                    elif peak_length < 15:
                                        response = 'Now that\'s what I call pyramid-farming Kappa // PogChamp // OSbury //'
                                    elif peak_length < 25:
                                        response = 'Wow, I can\'t even fit this pyramid in my memory bank MrDestructoid //'
                                    else:
                                        response = 'BUFFER OVERFLOW WutFace //'
                                    self.bot.say('{0} just finished a {1}-width {2} pyramid! {3}'.format(source.username_raw, peak_length, pyramid_thing, response))
                                self.data = []
                                self.going_down = False
                    else:
                        self.data = []
                        self.going_down = False
                else:
                    self.data = []
                    self.going_down = False

            if len(msg_parts) == 1 and len(self.data) == 0:
                self.data.append(msg_parts)
        except:
            # Let's just catch all exceptions, in case I fucked up in the above spaghetti code
            log.exception('Unhandled exception in pyramid parser')

    def enable(self, bot):
        if bot:
            bot.add_handler('on_pubmsg', self.on_pubmsg)
            self.bot = bot

    def disable(self, bot):
        if bot:
            bot.remove_handler('on_pubmsg', self.on_pubmsg)
