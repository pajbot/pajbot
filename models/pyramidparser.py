import re
import logging

log = logging.getLogger('tyggbot')


class PyramidParser:
    data = []
    regex = re.compile(' +')

    def __init__(self, bot):
        # Keep an instance of TyggBot so we can send messages from here!
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
                    for x in msg_parts:
                        if not x == pyramid_thing:
                            good = False
                            break

                    if good:
                        self.data.append(msg_parts)
                        if len_diff < 0:
                            if cur_len == 1:
                                # A pyramid was finished
                                peak_length = 0
                                for x in self.data:
                                    if len(x) > peak_length:
                                        peak_length = len(x)

                                response = 'PogChamp'
                                if peak_length <= 2:
                                    response = 'wow... ResidentSleeper //'
                                elif peak_length < 5:
                                    response = 'That\'s pretty neat KKona //'
                                elif peak_length < 7:
                                    response = 'Good job!!! PogChamp //'
                                else:
                                    response = 'Now that\'s what I call pyramid-farming Kappa // PogChamp // OSbury //'
                                self.bot.say('{0} just finished a {1}-width {2} pyramid {3}'.format(source.username_raw, peak_length, pyramid_thing, response))
                                self.data = []
                    else:
                        self.data = []
                else:
                    self.data = []

            if len(msg_parts) == 1 and len(self.data) == 0:
                self.data.append(msg_parts)
        except:
            # Let's just catch all exceptions, in case I fucked up in the above spaghetti code
            log.exception('Unhandled exception in pyramid parser')
