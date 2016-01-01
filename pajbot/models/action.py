import json
import logging
import collections

import irc
import regex as re

log = logging.getLogger('pajbot')


class ActionParser:
    bot = None

    def parse(raw_data=None, data=None):
        try:
            from pajbot.userdispatch import UserDispatch
            Dispatch = UserDispatch
        except ImportError:
            from pajbot.dispatch import Dispatch
        except:
            from pajbot.dispatch import Dispatch
            log.exception('Something went wrong while attemting to import UserDispatch')

        if not data:
            data = json.loads(raw_data)

        if data['type'] == 'say':
            action = SayAction(data['message'], ActionParser.bot)
        elif data['type'] == 'me':
            action = MeAction(data['message'], ActionParser.bot)
        elif data['type'] == 'whisper':
            action = WhisperAction(data['message'], ActionParser.bot)
        elif data['type'] == 'reply':
            action = ReplyAction(data['message'], ActionParser.bot)
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


def apply_substitutions(text, substitutions, bot, extra):
    for needle, sub in substitutions.items():
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
        text = text.replace(needle, str(value))

    return text


class IfSubstitution:
    def __call__(self, key, extra={}):
        if self.sub.key is None:
            msg = MessageAction.get_argument_value(extra.get('message', ''), self.sub.argument - 1)
            if msg:
                return self.get_true_response(extra)
            else:
                return self.get_false_response(extra)
        else:
            res = self.sub.cb(self.sub.key, extra)
            if res:
                return self.get_true_response(extra)
            else:
                return self.get_false_response(extra)

    def get_true_response(self, extra):
        return apply_substitutions(self.true_response, self.true_subs, self.bot, extra)

    def get_false_response(self, extra):
        return apply_substitutions(self.false_response, self.false_subs, self.bot, extra)

    def __init__(self, key, arguments, bot):
        self.bot = bot
        subs = get_substitutions(key, bot)
        if len(subs) == 1:
            self.sub = list(subs.values())[0]
        else:
            subs = get_argument_substitutions(key)
            if len(subs) == 1:
                self.sub = subs[0]
            else:
                self.sub = None
        self.true_response = arguments[0][2:-1] if len(arguments) > 0 else 'Yes'
        self.false_response = arguments[1][2:-1] if len(arguments) > 1 else 'No'

        self.true_subs = get_substitutions(self.true_response, bot)
        self.false_subs = get_substitutions(self.false_response, bot)


class Substitution:
    argument_substitution_regex = re.compile(r'\$\((\d+)\)')
    substitution_regex = re.compile(r'\$\(([a-z_]+)(\;[0-9]+)?(\:[\w\.\/ ]+|\:\$\([\w_:\._\/ ]+\))?(\|[\w]+(\([\w%: +-]+\))?)?(\,[\'"]{1}[\w $;_\-:()\.]+[\'"]{1}){0,2}\)')

    def __init__(self, cb, needle, key=None, argument=None, filter=None):
        self.cb = cb
        self.key = key
        self.argument = argument
        self.filter = filter
        self.needle = needle


class SubstitutionFilter:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class BaseAction:
    type = None
    subtype = None

    def reset(self):
        pass


class MultiAction(BaseAction):
    type = 'multi'

    def __init__(self, args, default=None, fallback=None):
        from pajbot.models.command import Command
        self.commands = {}
        self.default = default
        self.fallback = fallback

        for command in args:
            cmd = Command.from_json(command)
            for alias in command['command'].split('|'):
                if alias not in self.commands:
                    self.commands[alias] = cmd
                else:
                    log.error('Alias {0} for this multiaction is already in use.'.format(alias))

        import copy
        self.original_commands = copy.copy(self.commands)

    def reset(self):
        import copy
        self.commands = copy.copy(self.original_commands)

    def __iadd__(self, other):
        if other is not None and other.type == 'multi':
            self.commands.update(other.commands)
        return self

    @classmethod
    def ready_built(cls, commands, default=None, fallback=None):
        """ Useful if you already have a dictionary
        with commands pre-built.
        """

        multiaction = cls(args=[], default=default, fallback=fallback)
        multiaction.commands = commands
        import copy
        multiaction.original_commands = copy.copy(commands)
        return multiaction

    def run(self, bot, source, message, event={}, args={}):
        """ If there is more text sent to the multicommand after the
        initial alias, we _ALWAYS_ assume it's trying the subaction command.
        If the extra text was not a valid command, we try to run the fallback command.
        In case there's no extra text sent, we will try to run the default command.
        """

        cmd = None
        if message and len(message) > 0:
            msg_lower_parts = message.lower().split(' ')
            command = msg_lower_parts[0]
            cmd = self.commands.get(command, None)
            extra_msg = ' '.join(message.split(' ')[1:])
            if cmd is None and self.fallback:
                cmd = self.commands.get(self.fallback, None)
                extra_msg = message
        elif self.default:
            command = self.default
            cmd = self.commands.get(command, None)
            extra_msg = None

        if cmd:
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
        except:
            log.exception('Uncaught exception in FuncAction')


class RawFuncAction(BaseAction):
    type = 'rawfunc'

    def __init__(self, cb):
        self.cb = cb

    def run(self, bot, source, message, event={}, args={}):
        return self.cb(bot=bot, source=source, message=message, event=event, args=args)

def get_argument_substitutions(string):
    """
    Returns a list of `Substitution` objects that are found in the passed `string`.
    Will not return multiple `Substitution` objects for the same number.
    This means string "$(1) $(1) $(2)" will only return two Substitutions.
    """

    argument_substitutions = []

    for sub_key in Substitution.argument_substitution_regex.finditer(string):
        needle = sub_key.group(0)
        argument_num = int(sub_key.group(1))

        found = False
        for sub in argument_substitutions:
            if sub.argument == argument_num:
                # We already matched this argument variable
                found = True
                break
        if found:
            continue

        argument_substitutions.append(Substitution(None, needle=needle, argument=argument_num))

    return argument_substitutions

def get_substitution_arguments(sub_key):
    sub_string = sub_key.group(0)
    path = sub_key.group(1)
    argument = sub_key.group(2)
    if argument is not None:
        argument = int(argument[1:])
    key = sub_key.group(3)
    if key is not None:
        key = key[1:]
    filter = sub_key.group(4)
    filter_arguments = []
    if filter is not None:
        filter = filter[1:]
        filter_arguments = sub_key.group(5)
        if filter_arguments is not None:
            filter = filter[:-len(filter_arguments)]
            filter_arguments = [filter_arguments[1:-1]]
        else:
            filter_arguments = []
        filter = SubstitutionFilter(filter, filter_arguments)
    if_arguments = sub_key.captures(6)

    return sub_string, path, argument, key, filter, if_arguments


def get_substitutions(string, bot):
    """
    Returns a dictionary of `Substitution` objects thare are found in the passed `string`.
    Will not return multiple `Substitution` objects for the same string.
    This means "You have $(source:points) points xD $(source:points)" only returns one Substitution.
    """

    substitutions = collections.OrderedDict()

    for sub_key in Substitution.substitution_regex.finditer(string):
        sub_string, path, argument, key, filter, if_arguments = get_substitution_arguments(sub_key)

        if sub_string in substitutions:
            # We already matched this variable
            continue

        try:
            if path == 'if':
                if len(if_arguments) > 0:
                    if_substitution = IfSubstitution(key, if_arguments, bot)
                    if if_substitution.sub is None:
                        continue
                    sub = Substitution(if_substitution, needle=sub_string, key=key, argument=argument, filter=filter)
                    substitutions[sub_string] = sub
        except:
            log.exception('BabyRage')

    method_mapping = {}
    try:
        method_mapping['kvi'] = bot.get_kvi_value
        method_mapping['tb'] = bot.get_value
        method_mapping['lasttweet'] = bot.get_last_tweet
        method_mapping['etm'] = bot.get_emote_tm
        method_mapping['ecount'] = bot.get_emote_count
        method_mapping['etmrecord'] = bot.get_emote_tm_record
        method_mapping['source'] = bot.get_source_value
        method_mapping['user'] = bot.get_user_value
        method_mapping['usersource'] = bot.get_usersource_value
        method_mapping['time'] = bot.get_time_value
        method_mapping['curdeck'] = bot.decks.action_get_curdeck
        method_mapping['current_stream'] = bot.stream_manager.get_current_stream_value
        method_mapping['last_stream'] = bot.stream_manager.get_last_stream_value
        method_mapping['current_song'] = bot.get_current_song_value
    except AttributeError:
        pass

    for sub_key in Substitution.substitution_regex.finditer(string):
        sub_string, path, argument, key, filter, if_arguments = get_substitution_arguments(sub_key)

        if sub_string in substitutions:
            # We already matched this variable
            continue

        if path in method_mapping:
            sub = Substitution(method_mapping[path], needle=sub_string, key=key, argument=argument, filter=filter)
            substitutions[sub_string] = sub

    return substitutions


class MessageAction(BaseAction):
    type = 'message'

    def __init__(self, response, bot):
        self.response = response
        if bot:
            self.argument_subs = get_argument_substitutions(self.response)
            self.subs = get_substitutions(self.response, bot)
        else:
            self.argument_subs = []
            self.subs = {}

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

        resp = apply_substitutions(resp, self.subs, bot, extra)

        if resp is None:
            return None

        for sub in self.argument_subs:
            needle = sub.needle
            value = str(MessageAction.get_argument_value(extra['message'], sub.argument - 1))
            resp = resp.replace(needle, value)
            log.debug('Replacing {0} with {1}'.format(needle, value))

        return resp

    def get_extra_data(self, source, message):
        return {
                'user': source.username if source else None,
                'source': source,
                'message': message,
                }

    def run(self, bot, source, message, event={}, args={}):
        raise NotImplementedError('Please implement the run method.')


class SayAction(MessageAction):
    subtype = 'say'

    def run(self, bot, source, message, event={}, args={}):
        resp = self.get_response(bot, self.get_extra_data(source, message))
        if resp:
            bot.say(resp)


class MeAction(MessageAction):
    subtype = 'me'

    def run(self, bot, source, message, event={}, args={}):
        resp = self.get_response(bot, self.get_extra_data(source, message))
        if resp:
            bot.me(resp)


class WhisperAction(MessageAction):
    subtype = 'whisper'

    def run(self, bot, source, message, event={}, args={}):
        resp = self.get_response(bot, self.get_extra_data(source, message))
        if resp:
            bot.whisper(source.username, resp)


class ReplyAction(MessageAction):
    subtype = 'reply'

    def run(self, bot, source, message, event={}, args={}):
        resp = self.get_response(bot, self.get_extra_data(source, message))
        if resp:
            if irc.client.is_channel(event.target):
                bot.say(resp, channel=event.target)
            else:
                bot.whisper(source.username, resp)
