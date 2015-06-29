import json, re, logging

from tyggbot import TyggBot
from command import Command
from dispatch import Dispatch

log = logging.getLogger('tyggbot')

class BaseAction:
    type = '??'

class MultiAction(BaseAction):
    type = 'multi'

    def __init__(self, args, default):
        self.commands = {}
        self.default = default

        for command in args:
            cmd = Command.from_json(command)
            self.commands[command['command']] = cmd

    def run(self, tyggbot, source, message, event={}, args={}):
        if message:
            msg_lower_parts = message.lower().split(' ')
            command = msg_lower_parts[0]
            extra_msg = ' '.join(message.split(' ')[1:])
        else:
            command = self.default
            extra_msg = None

        if command in self.commands:
            cmd = self.commands[command]
            if source.level >= cmd.level:
                cmd.run(tyggbot, source, extra_msg, event, args)
                return
            else:
                log.info('User {0} tried running a sub-command he had no access to ({1}).'.format(source.username, command))
                return

class FuncAction(BaseAction):
    type = 'func'

    def __init__(self, cb):
        self.cb = cb

    def run(self, tyggbot, source, message, event={}, args={}):
        try:
            self.cb(tyggbot, source, message, event, args)
        except Exception as e:
            log.error('Uncaught exception: {0}'.format(e))

class RawFuncAction(BaseAction):
    type = 'rawfunc'

    def __init__(self, cb):
        self.cb = cb

    def run(self, tyggbot, source, message, event={}, args={}):
        self.cb()

class SayAction(BaseAction):
    regex = re.compile('(\$\([a-zA-Z:_0-9]+\))')
    inner_regex = re.compile('([a-z]+:|)([a-zA-Z_0-9]+)')
    type = 'say'

    def __init__(self, response):
        self.response = response
        self.subs = {}

        self.init_parse()

    def init_parse(self):
        for sub_key in self.regex.findall(self.response):
            if sub_key in self.subs:
                # We already matched this variable
                continue

            inner_match = self.inner_regex.search(sub_key)

            if inner_match:
                path = inner_match.group(1)
                key = inner_match.group(2)
                if len(path) == 0:
                    path = 'tb'
                else:
                    path = path[:-1]

                if path == 'kvi':
                    cb = TyggBot.instance.get_kvi_value
                elif path == 'tb':
                    cb = TyggBot.instance.get_value
                elif path == 'lasttweet':
                    cb = TyggBot.instance.get_last_tweet
                else:
                    log.error('Unimplemented path: {0}'.format(path))
                    continue

            self.subs[sub_key] = (cb, key)

    # XXX: Is a regex replace faster than a normal string replace?
    def get_response(self, tyggbot, extra):
        resp = self.response

        for needle, tup in self.subs.items():
            value = str(tup[0](tup[1], extra))
            log.debug('Replace {0} with {1}'.format(needle, value))
            resp = resp.replace(needle, value)
            log.debug(resp)

        return resp

    def run(self, tyggbot, source, message, event={}, args={}):
        tyggbot.say(self.get_response(tyggbot, {'user':source.username}))
