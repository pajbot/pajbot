import json
import re
import logging

log = logging.getLogger('tyggbot')


class ActionParser:
    bot = None

    def parse(raw_data=None, data=None):
        try:
            from tyggbot.userdispatch import UserDispatch
            Dispatch = UserDispatch
        except ImportError:
            from tyggbot.dispatch import Dispatch
        except:
            from tyggbot.dispatch import Dispatch
            log.exception('Something went wrong while attemting to import UserDispatch')

        if not data:
            data = json.loads(raw_data)

        if data['type'] == 'say':
            action = SayAction(data['message'], ActionParser.bot)
        elif data['type'] == 'me':
            action = MeAction(data['message'], ActionParser.bot)
        elif data['type'] == 'whisper':
            action = WhisperAction(data['message'], ActionParser.bot)
        elif data['type'] == 'func':
            try:
                action = FuncAction(getattr(Dispatch, data['cb']))
            except AttributeError as e:
                log.error('AttributeError caught when parsing action: {0}'.format(e))
                return None
        elif data['type'] == 'multi':
            action = MultiAction(data['args'], data['default'])
        else:
            raise Exception('Unknown action type: {0}'.format(data['type']))

        return action


class Substitution:
    def __init__(self, cb, key=None, argument=None, filter=None):
        self.cb = cb
        self.key = key
        self.argument = argument
        self.filter = filter


class SubstitutionFilter:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class BaseAction:
    type = '??'


class MultiAction(BaseAction):
    type = 'multi'

    def __init__(self, args, default):
        from tyggbot.models.command import Command
        self.commands = {}
        self.default = default

        for command in args:
            cmd = Command.from_json(command)
            for alias in command['command'].split('|'):
                if alias not in self.commands:
                    self.commands[alias] = cmd
                else:
                    log.error('Alias {0} for this multiaction is already in use.'.format(alias))

    @classmethod
    def ready_built(cls, commands):
        """Useful if you already have a dictionary
        with commands pre-built.
        """

        multiaction = cls(args=[], default=None)
        multiaction.commands = commands
        return multiaction

    def run(self, bot, source, message, event={}, args={}):
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
                return cmd.run(bot, source, extra_msg, event, args)
            else:
                log.info('User {0} tried running a sub-command he had no access to ({1}).'.format(source.username, command))


class FuncAction(BaseAction):
    type = 'func'

    def __init__(self, cb):
        self.cb = cb

    def run(self, bot, source, message, event={}, args={}):
        try:
            return self.cb(bot, source, message, event, args)
        except Exception:
            log.exception('Uncaught exception in FuncAction')


class RawFuncAction(BaseAction):
    type = 'rawfunc'

    def __init__(self, cb):
        self.cb = cb

    def run(self, bot, source, message, event={}, args={}):
        return self.cb()


class MessageAction(BaseAction):
    type = 'message'
    regex = re.compile(r'\$\(([a-z]+)(;[0-9]+)?(:[\w/ ]+)?(\|[a-zA-Z0-9]+(\([\w%: +-]+\))?)?\)')
    argument_regex = re.compile('(\$\([0-9]+\))')
    argument_inner_regex = re.compile('\$\(([0-9]+)\)')

    def __init__(self, response, bot):
        self.response = response
        self.argument_subs = []
        self.subs = {}

        self.init_parse(bot)

    def init_parse(self, bot):
        from tyggbot.tyggbot import TyggBot
        for sub_key in self.argument_regex.findall(self.response):
            inner_match = self.argument_inner_regex.search(sub_key)
            if inner_match:
                argument_num = inner_match.group(1)
                try:
                    argument_num = int(argument_num)
                except:
                    continue

                found = False
                for sub in self.argument_subs:
                    if sub.argument == argument_num:
                        # We already matched this argument variable
                        found = True
                        break
                if found:
                    continue

                self.argument_subs.append(Substitution(None, argument=argument_num))

        for sub_key in self.regex.finditer(self.response):
            sub_string = sub_key.group(0)
            path = sub_key.group(1)
            argument = sub_key.group(2)
            if argument is not None:
                argument = int(argument[1:])
            key = sub_key.group(3)
            if key is not None:
                key = key[1:]
            filter = sub_key.group(4)
            if filter is not None:
                filter = filter[1:]
                filter_argument = sub_key.group(5)
                if filter_argument is not None:
                    filter = filter[:-len(filter_argument)]
                    filter_argument = [filter_argument[1:-1]]
                else:
                    filter_argument = []
                filter = SubstitutionFilter(filter, filter_argument)

            if sub_string in self.subs:
                # We already matched this variable
                continue

            try:
                if path == 'kvi':
                    cb = bot.get_kvi_value
                elif path == 'tb':
                    cb = bot.get_value
                elif path == 'lasttweet':
                    cb = bot.get_last_tweet
                elif path == 'etm':
                    cb = bot.get_emote_tm
                elif path == 'ecount':
                    cb = bot.get_emote_count
                elif path == 'etmrecord':
                    cb = bot.get_emote_tm_record
                elif path == 'source':
                    cb = bot.get_source_value
                elif path == 'user':
                    cb = bot.get_user_value
                elif path == 'time':
                    cb = bot.get_time_value
                elif path == 'curdeck':
                    cb = bot.decks.action_get_curdeck
                else:
                    log.error('Unimplemented path: {0}'.format(path))
                    continue
            except:
                continue

            sub = Substitution(cb, key=key, argument=argument, filter=filter)
            self.subs[sub_string] = sub

    def get_argument_value(message, index):
        if not message:
            return ''
        msg_parts = message.split(' ')
        try:
            return msg_parts[index]
        except:
            pass
        return ''

    def get_response(self, bot, extra):
        resp = self.response

        for sub in self.argument_subs:
            needle = '$({0})'.format(sub.argument)
            value = str(MessageAction.get_argument_value(extra['message'], sub.argument - 1))
            resp = resp.replace(needle, value)
            log.debug('Replacing {0} with {1}'.format(needle, value))

        for needle, sub in self.subs.items():
            if sub.key and sub.argument:
                param = sub.key
                extra['argument'] = MessageAction.get_argument_value(extra['message'], sub.argument - 1)
            elif sub.key:
                param = sub.key
            elif sub.argument:
                param = MessageAction.get_argument_value(extra['message'], sub.argument - 1)
            else:
                log.error('Unknown param for response.')
                continue
            value = sub.cb(param, extra)
            try:
                if sub.filter is not None:
                    value = bot.apply_filter(value, sub.filter)
            except:
                pass
            if value is None:
                return None
            resp = resp.replace(needle, str(value))
            log.debug('Replacing {0} with {1}'.format(needle, str(value)))

        return resp

    def get_extra_data(self, source, message):
        return {
                'user': source.username,
                'source': source,
                'message': message,
                }

    def run(self, bot, source, message, event={}, args={}):
        raise NotImplementedError('Please implement the run method.')


class SayAction(MessageAction):
    def run(self, bot, source, message, event={}, args={}):
        resp = self.get_response(bot, self.get_extra_data(source, message))
        if resp:
            bot.say(resp)


class MeAction(MessageAction):
    def run(self, bot, source, message, event={}, args={}):
        resp = self.get_response(bot, self.get_extra_data(source, message))
        if resp:
            bot.me(resp)


class WhisperAction(MessageAction):
    def run(self, bot, source, message, event={}, args={}):
        resp = self.get_response(bot, self.get_extra_data(source, message))
        if resp:
            bot.whisper(source.username, resp)
