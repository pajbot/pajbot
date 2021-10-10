from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

import cgi
import collections
import json
import logging
import sys

import irc
import regex as re
import requests

if TYPE_CHECKING:
    from pajbot.bot import Bot

from pajbot.managers.schedule import ScheduleManager

log = logging.getLogger(__name__)


class ActionParser:
    bot: Optional[Bot] = None

    @staticmethod
    def parse(
        str_data: Optional[str] = None, dict_data: Optional[Dict[str, str]] = None, command=""
    ) -> Optional[BaseAction]:
        try:
            from pajbot.userdispatch import UserDispatch

            Dispatch = UserDispatch
        except ImportError:
            from pajbot.dispatch import Dispatch as NormalDispatch

            Dispatch = NormalDispatch
        except:
            log.exception("Something went wrong while attemting to import Dispatch, this should never happen")
            sys.exit(1)

        data: Dict[str, str] = {}

        if dict_data is not None:
            data = dict_data
        else:
            if not str_data:
                raise Exception("raw_data must be set if input_data is not set")

            json_data = json.loads(str_data)
            if not isinstance(json_data, dict):
                raise Exception("raw_data must be a JSON object string")

            data = json_data

        if data["type"] == "say":
            return SayAction(data["message"], ActionParser.bot)
        elif data["type"] == "me":
            return MeAction(data["message"], ActionParser.bot)
        elif data["type"] == "whisper":
            return WhisperAction(data["message"], ActionParser.bot)
        elif data["type"] == "reply":
            return ReplyAction(data["message"], ActionParser.bot)
        elif data["type"] == "func":
            try:
                return FuncAction(getattr(Dispatch, data["cb"]))
            except AttributeError as e:
                log.error(f'AttributeError caught when parsing action for action "{command}": {e}')
                return None
        elif data["type"] == "multi":
            return MultiAction(data["args"], data["default"])
        else:
            raise Exception(f"Unknown action type: {data['type']}")

        return None


class IfSubstitution:
    def __call__(self, key, extra={}):
        if self.sub.key is None:
            msg = MessageAction.get_argument_value(extra.get("message", ""), self.sub.argument - 1)
            if msg:
                return self.get_true_response(extra)

            return self.get_false_response(extra)

        res = self.sub.cb(self.sub.key, extra)
        if res:
            return self.get_true_response(extra)

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
        self.true_response = arguments[0][2:-1] if arguments else "Yes"
        self.false_response = arguments[1][2:-1] if len(arguments) > 1 else "No"

        self.true_subs = get_substitutions(self.true_response, bot)
        self.false_subs = get_substitutions(self.false_response, bot)


class SubstitutionFilter:
    def __init__(self, name: str, arguments: List[str]):
        self.name = name
        self.arguments = arguments


class Substitution:
    argument_substitution_regex = re.compile(r"\$\((\d+)\)")
    substitution_regex = re.compile(
        r'\$\(([a-z_]+)(\;[0-9]+)?(\:[\w\.\/ -]+|\:\$\([\w_:;\._\/ -]+\))?(\|[\w]+(\([\w%:/ +-.]+\))?)*(\,[\'"]{1}[\w \|$;_\-:()\.]+[\'"]{1}){0,2}\)'
    )
    # https://stackoverflow.com/a/7109208
    urlfetch_substitution_regex = re.compile(r"\$\(urlfetch ([A-Za-z0-9\-._~:/?#\[\]@!$%&\'()*+,;=]+)\)")
    urlfetch_substitution_regex_all = re.compile(r"\$\(urlfetch (.+?)\)")

    def __init__(self, cb, needle, key=None, argument=None, filters: List[SubstitutionFilter] = []):
        self.cb = cb
        self.key = key
        self.argument = argument
        self.filters = filters
        self.needle = needle


class BaseAction:
    type: Optional[str] = None
    subtype: Optional[str] = None

    def reset(self):
        pass


class MultiAction(BaseAction):
    type = "multi"

    def __init__(self, args, default=None, fallback=None):
        from pajbot.models.command import Command

        self.commands = {}
        self.default = default
        self.fallback = fallback

        for command in args:
            cmd = Command.from_json(command)
            for alias in command["command"].split("|"):
                if alias not in self.commands:
                    self.commands[alias] = cmd
                else:
                    log.error(f"Alias {alias} for this multiaction is already in use.")

        import copy

        self.original_commands = copy.copy(self.commands)

    def reset(self):
        import copy

        self.commands = copy.copy(self.original_commands)

    def __iadd__(self, other):
        if other is not None and other.type == "multi":
            self.commands.update(other.commands)
        return self

    @classmethod
    def ready_built(cls, commands, default=None, fallback=None):
        """Useful if you already have a dictionary
        with commands pre-built.
        """

        multiaction = cls(args=[], default=default, fallback=fallback)
        multiaction.commands = commands
        import copy

        multiaction.original_commands = copy.copy(commands)
        return multiaction

    def run(self, bot, source, message, event={}, args={}):
        """If there is more text sent to the multicommand after the
        initial alias, we _ALWAYS_ assume it's trying the subaction command.
        If the extra text was not a valid command, we try to run the fallback command.
        In case there's no extra text sent, we will try to run the default command.
        """

        cmd = None
        if message:
            msg_lower_parts = message.lower().split(" ")
            command = msg_lower_parts[0]
            cmd = self.commands.get(command, None)
            extra_msg = " ".join(message.split(" ")[1:])
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

            log.info(f"User {source} tried running a sub-command he had no access to ({command}).")

        return None


class FuncAction(BaseAction):
    type = "func"

    def __init__(self, cb):
        self.cb = cb

    def run(self, bot, source, message, event={}, args={}):
        try:
            return self.cb(bot, source, message, event, args)
        except:
            log.exception("Uncaught exception in FuncAction")


class RawFuncAction(BaseAction):
    type = "rawfunc"

    def __init__(self, cb):
        self.cb = cb

    def run(self, bot, source, message, event={}, args={}):
        return self.cb(bot=bot, source=source, message=message, event=event, args=args)


def get_argument_substitutions(string: str) -> List[Substitution]:
    """
    Returns a list of `Substitution` objects that are found in the passed `string`.
    Will not return multiple `Substitution` objects for the same number.
    This means string "$(1) $(1) $(2)" will only return two Substitutions.
    """

    argument_substitutions: List[Substitution] = []

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
    matched_filters = sub_key.captures(4)
    matched_filter_arguments = sub_key.captures(5)

    filters: List[SubstitutionFilter] = []
    filter_argument_index = 0
    for f in matched_filters:
        f = f[1:]
        filter_arguments: List[str] = []
        if "(" in f:
            f = f[: -len(matched_filter_arguments[filter_argument_index])]
            filter_arguments = [matched_filter_arguments[filter_argument_index][1:-1]]
            filter_argument_index += 1

        f = SubstitutionFilter(f, filter_arguments)
        filters.append(f)

    if_arguments = sub_key.captures(6)

    return sub_string, path, argument, key, filters, if_arguments


def get_substitutions(string: str, bot: Bot) -> Dict[str, Substitution]:
    """
    Returns a dictionary of `Substitution` objects thare are found in the passed `string`.
    Will not return multiple `Substitution` objects for the same string.
    This means "You have $(source:points) points xD $(source:points)" only returns one Substitution.
    """

    substitutions = collections.OrderedDict()

    for sub_key in Substitution.substitution_regex.finditer(string):
        sub_string, path, argument, key, filters, if_arguments = get_substitution_arguments(sub_key)

        if sub_string in substitutions:
            # We already matched this variable
            continue

        try:
            if path == "if":
                if if_arguments:
                    if_substitution = IfSubstitution(key, if_arguments, bot)
                    if if_substitution.sub is None:
                        continue
                    sub = Substitution(if_substitution, needle=sub_string, key=key, argument=argument, filters=filters)
                    substitutions[sub_string] = sub
        except:
            log.exception("BabyRage")

    method_mapping = {}
    try:
        method_mapping["kvi"] = bot.get_kvi_value
        method_mapping["tb"] = bot.get_value
        method_mapping["lasttweet"] = bot.get_last_tweet
        # "etm" is legacy
        method_mapping["etm"] = bot.get_emote_epm
        method_mapping["epm"] = bot.get_emote_epm
        method_mapping["etmrecord"] = bot.get_emote_epm_record
        method_mapping["epmrecord"] = bot.get_emote_epm_record
        method_mapping["ecount"] = bot.get_emote_count
        method_mapping["source"] = bot.get_source_value
        method_mapping["user"] = bot.get_user_value
        method_mapping["usersource"] = bot.get_usersource_value
        method_mapping["time"] = bot.get_time_value
        method_mapping["date"] = bot.get_date_value
        method_mapping["datetimefromisoformat"] = bot.get_datetimefromisoformat_value
        method_mapping["datetime"] = bot.get_datetime_value
        method_mapping["curdeck"] = bot.decks.action_get_curdeck
        method_mapping["stream"] = bot.stream_manager.get_stream_value
        method_mapping["current_stream"] = bot.stream_manager.get_current_stream_value
        method_mapping["last_stream"] = bot.stream_manager.get_last_stream_value
        method_mapping["current_song"] = bot.get_current_song_value
        method_mapping["args"] = bot.get_args_value
        method_mapping["strictargs"] = bot.get_strictargs_value
        method_mapping["command"] = bot.get_command_value
        method_mapping["broadcaster"] = bot.get_broadcaster_value
    except AttributeError:
        pass

    for sub_key in Substitution.substitution_regex.finditer(string):
        sub_string, path, argument, key, filters, if_arguments = get_substitution_arguments(sub_key)

        if sub_string in substitutions:
            # We already matched this variable
            continue

        if path in method_mapping:
            sub = Substitution(method_mapping[path], needle=sub_string, key=key, argument=argument, filters=filters)
            substitutions[sub_string] = sub

    return substitutions


def get_urlfetch_substitutions(string, all=False):
    substitutions = {}

    if all:
        r = Substitution.urlfetch_substitution_regex_all
    else:
        r = Substitution.urlfetch_substitution_regex

    for sub_key in r.finditer(string):
        substitutions[sub_key.group(0)] = sub_key.group(1)

    return substitutions


def is_message_good(bot, message, extra):
    # this is imported here to avoid circular imports
    # (Circular import was command.py importing this file)
    from pajbot.modules.ascii import AsciiProtectionModule

    checks = {
        "banphrase": lambda: bot.banphrase_manager.check_message(message, extra["source"]),
        "ascii": lambda: AsciiProtectionModule.check_message(message),
        "massping": lambda: bot.module_manager.get_module("massping").check_message(message, extra["source"]),
    }

    for check_name, check_fn in checks.items():
        # Make sure the module is enabled
        if check_name not in bot.module_manager:
            continue

        # apply the check fn
        # only if the result is False the check was successful
        if check_fn() is not False:
            log.info(f'Not sending message "{message}" because check "{check_name}" failed.')
            return False

    return True


class MessageAction(BaseAction):
    type = "message"

    def __init__(self, response: str, bot: Optional[Bot]):
        self.response = response

        self.argument_subs: List[Substitution] = []
        self.subs: Dict[str, Substitution] = {}
        self.num_urlfetch_subs = 0

        if bot:
            self.argument_subs = get_argument_substitutions(self.response)
            self.subs = get_substitutions(self.response, bot)
            self.num_urlfetch_subs = len(get_urlfetch_substitutions(self.response, all=True))

    @staticmethod
    def get_argument_value(message, index):
        if not message:
            return ""
        msg_parts = message.split(" ")
        try:
            return msg_parts[index]
        except:
            pass
        return ""

    def get_response(self, bot: Bot, extra) -> Optional[str]:
        resp = self.response

        resp = apply_substitutions(resp, self.subs, bot, extra)

        if resp is None:
            return None

        for sub in self.argument_subs:
            needle = sub.needle
            value = str(MessageAction.get_argument_value(extra["message"], sub.argument - 1))
            resp = resp.replace(needle, value)
            log.debug(f"Replacing {needle} with {value}")

        if "command" in extra and extra["command"].run_through_banphrases is True and "source" in extra:
            if not is_message_good(bot, resp, extra):
                return None

        return resp

    @staticmethod
    def get_extra_data(source, message, args):
        return {"source": source, "message": message, **args}

    def run(self, bot, source, message, event={}, args={}):
        raise NotImplementedError("Please implement the run method.")


def urlfetch_msg(method, message, num_urlfetch_subs, bot, extra={}, args=[], kwargs={}):
    urlfetch_subs = get_urlfetch_substitutions(message)

    if len(urlfetch_subs) > num_urlfetch_subs:
        log.error(f"HIJACK ATTEMPT {message}")
        return False

    for needle, url in urlfetch_subs.items():
        headers = {
            "Accept": "text/plain",
            "Accept-Language": "en-US, en;q=0.9, *;q=0.5",
            "User-Agent": bot.user_agent,
        }
        r = requests.get(url, allow_redirects=True, headers=headers)
        if r.status_code == requests.codes.ok:
            # For "legacy" reasons, we don't check the content type of ok status codes
            value = r.text.strip().replace("\n", "").replace("\r", "")[:400]
        else:
            # An error code was returned, ensure the response is plain text
            content_type = r.headers["Content-Type"]
            if content_type is not None and cgi.parse_header(content_type)[0] != "text/plain":
                # The content type is not plain text, return a generic error showing the status code returned
                value = f"urlfetch error {r.status_code}"
            else:
                value = r.text.strip().replace("\n", "").replace("\r", "")[:400]

        message = message.replace(needle, value)

    if "command" in extra and extra["command"].run_through_banphrases is True and "source" in extra:
        if not is_message_good(bot, message, extra):
            return None

    args.append(message)

    method(*args, **kwargs)


class SayAction(MessageAction):
    subtype = "say"

    def run(self, bot, source, message, event={}, args={}):
        extra = self.get_extra_data(source, message, args)
        resp = self.get_response(bot, extra)

        if not resp:
            return False

        if self.num_urlfetch_subs == 0:
            return bot.say(resp)

        return ScheduleManager.execute_now(
            urlfetch_msg,
            args=[],
            kwargs={
                "args": [],
                "kwargs": {},
                "method": bot.say,
                "bot": bot,
                "extra": extra,
                "message": resp,
                "num_urlfetch_subs": self.num_urlfetch_subs,
            },
        )


class MeAction(MessageAction):
    subtype = "me"

    def run(self, bot, source, message, event={}, args={}):
        extra = self.get_extra_data(source, message, args)
        resp = self.get_response(bot, extra)

        if not resp:
            return False

        if self.num_urlfetch_subs == 0:
            return bot.me(resp)

        return ScheduleManager.execute_now(
            urlfetch_msg,
            args=[],
            kwargs={
                "args": [],
                "kwargs": {},
                "method": bot.me,
                "bot": bot,
                "extra": extra,
                "message": resp,
                "num_urlfetch_subs": self.num_urlfetch_subs,
            },
        )


class WhisperAction(MessageAction):
    subtype = "whisper"

    def run(self, bot, source, message, event={}, args={}):
        extra = self.get_extra_data(source, message, args)
        resp = self.get_response(bot, extra)

        if not resp:
            return False

        if self.num_urlfetch_subs == 0:
            return bot.whisper(source, resp)

        return ScheduleManager.execute_now(
            urlfetch_msg,
            args=[],
            kwargs={
                "args": [source],
                "kwargs": {},
                "method": bot.whisper,
                "bot": bot,
                "extra": extra,
                "message": resp,
                "num_urlfetch_subs": self.num_urlfetch_subs,
            },
        )


class ReplyAction(MessageAction):
    subtype = "reply"

    def run(self, bot, source, message, event={}, args={}):
        extra = self.get_extra_data(source, message, args)
        resp = self.get_response(bot, extra)

        if not resp:
            return False

        if irc.client.is_channel(event.target):
            if self.num_urlfetch_subs == 0:
                return bot.reply(extra["msg_id"], resp, channel=event.target)

            return ScheduleManager.execute_now(
                urlfetch_msg,
                args=[],
                kwargs={
                    "args": [],
                    "kwargs": {"channel": event.target},
                    "method": bot.say,
                    "bot": bot,
                    "extra": extra,
                    "message": resp,
                    "num_urlfetch_subs": self.num_urlfetch_subs,
                },
            )

        if self.num_urlfetch_subs == 0:
            return bot.whisper(source, resp)

        return ScheduleManager.execute_now(
            urlfetch_msg,
            args=[],
            kwargs={
                "args": [source],
                "kwargs": {},
                "method": bot.whisper,
                "bot": bot,
                "extra": extra,
                "message": resp,
                "num_urlfetch_subs": self.num_urlfetch_subs,
            },
        )


def apply_substitutions(text, substitutions: Dict[Any, Substitution], bot: Bot, extra):
    for needle, sub in substitutions.items():
        if sub.key and sub.argument:
            param = sub.key
            extra["argument"] = MessageAction.get_argument_value(extra["message"], sub.argument - 1)
        elif sub.key:
            param = sub.key
        elif sub.argument:
            param = MessageAction.get_argument_value(extra["message"], sub.argument - 1)
        else:
            log.error("Unknown param for response.")
            continue
        value: Any = sub.cb(param, extra)
        if value is None:
            return None
        try:
            for f in sub.filters:
                value = bot.apply_filter(value, f)
        except:
            log.exception("Exception caught in filter application")
        if value is None:
            return None
        text = text.replace(needle, str(value))

    return text
