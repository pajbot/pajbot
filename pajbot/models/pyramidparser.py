import re
import logging

log = logging.getLogger('pajbot')


class PyramidParser:
    data = []
    going_down = False
    regex = re.compile(' +')

    def __init__(self, bot):
        self.bot = bot

    def parse_line(self, msg, source):
        try:
            msg_parts = msg.split(' ')
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
