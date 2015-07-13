import json, re, logging

from tyggbot import TyggBot
from command import Command

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
            for alias in command['command'].split('|'):
                if alias not in self.commands:
                    self.commands[alias] = cmd
                else:
                    log.error('Alias {0} for this multiaction is already in use.'.format(alias))

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
                return cmd.run(tyggbot, source, extra_msg, event, args)
            else:
                log.info('User {0} tried running a sub-command he had no access to ({1}).'.format(source.username, command))

class FuncAction(BaseAction):
    type = 'func'

    def __init__(self, cb):
        self.cb = cb

    def run(self, tyggbot, source, message, event={}, args={}):
        try:
            return self.cb(tyggbot, source, message, event, args)
        except Exception as e:
            log.exception('Uncaught exception in FuncAction')

class RawFuncAction(BaseAction):
    type = 'rawfunc'

    def __init__(self, cb):
        self.cb = cb

    def run(self, tyggbot, source, message, event={}, args={}):
        return self.cb()

class MessageAction(BaseAction):
    type = 'message'
    regex = re.compile('(\$\([a-zA-Z:_0-9 ]+\))')
    inner_regex = re.compile('([a-z]+:|)([a-zA-Z_0-9 ]+)')

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
                elif path == 'epm':
                    cb = TyggBot.instance.get_emote_pm
                elif path == 'etm':
                    cb = TyggBot.instance.get_emote_tm
                elif path == 'ecount':
                    cb = TyggBot.instance.get_emote_count
                elif path == 'epmrecord':
                    cb = TyggBot.instance.get_emote_pm_record
                elif path == 'etmrecord':
                    cb = TyggBot.instance.get_emote_tm_record
                else:
                    log.error('Unimplemented path: {0}'.format(path))
                    continue

            self.subs[sub_key] = (cb, key)

    def get_response(self, tyggbot, extra):
        resp = self.response

        for needle, tup in self.subs.items():
            value = str(tup[0](tup[1], extra))
            log.debug('Replace {0} with {1}'.format(needle, value))
            resp = resp.replace(needle, value)
            log.debug(resp)

        return resp

    def run(self, tyggbot, source, message, event={}, args={}):
        raise NotImplementedError('Please implement the run method.')

class SayAction(MessageAction):
    def run(self, tyggbot, source, message, event={}, args={}):
        tyggbot.say(self.get_response(tyggbot, {'user':source.username}))

class MeAction(MessageAction):
    def run(self, tyggbot, source, message, event={}, args={}):
        tyggbot.me(self.get_response(tyggbot, {'user':source.username}))
