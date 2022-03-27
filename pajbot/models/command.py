from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

import datetime
import json
import logging
import re

import pajbot.utils
from pajbot.exc import FailedCommand
from pajbot.managers.db import Base
from pajbot.managers.schedule import ScheduleManager
from pajbot.models.action import ActionParser, BaseAction, MessageAction, MultiAction, RawFuncAction, Substitution
from pajbot.models.user import User

from sqlalchemy import BOOLEAN, INT, TEXT, Column, ForeignKey
from sqlalchemy.orm import reconstructor, relationship
from sqlalchemy_utc import UtcDateTime

if TYPE_CHECKING:
    from pajbot.bot import Bot

log = logging.getLogger(__name__)


def parse_command_for_web(alias: str, i_command: Command, command_list: List[WebCommand]) -> None:
    import markdown
    from markupsafe import Markup

    for c in command_list:
        if c._command == i_command:
            return

    command = WebCommand(alias, i_command)

    try:
        if command.description is not None:
            json_description = json.loads(command.description)
            if isinstance(json_description, dict):
                command.json_description = json_description
                if "description" in command.json_description:
                    command.parsed_description = Markup(markdown.markdown(command.json_description["description"]))
                if command.json_description.get("hidden", False) is True:
                    return
    except ValueError:
        # Invalid JSON
        pass
    except:
        log.warning(command.json_description)
        log.exception("Unhandled exception BabyRage")
        return

    if command.command is None:
        command.command = alias

    if command.action is not None and command.action.type == "multi" and isinstance(command.action, MultiAction):
        if command.command is not None:
            command.main_alias = command.command.split("|")[0]
        for inner_alias, inner_command in command.action.commands.items():
            parse_command_for_web(
                alias if command.command is None else command.main_alias + " " + inner_alias,
                inner_command,
                command_list,
            )
    else:
        test = re.compile(r"[^\w]")
        first_alias = command.command.split("|")[0]
        command.resolve_string = test.sub("", first_alias.replace(" ", "_"))
        command.main_alias = "!" + first_alias
        if not command.parsed_description:
            if command.action is not None:
                if command.action.type == "message" and isinstance(command.action, MessageAction):
                    command.parsed_description = command.action.response
                    if not command.action.response:
                        return
            if command.description is not None:
                command.parsed_description = command.description
        command_list.append(command)


class CommandData(Base):
    __tablename__ = "command_data"

    command_id = Column(INT, ForeignKey("command.id", ondelete="CASCADE"), primary_key=True, autoincrement=False)
    num_uses = Column(INT, nullable=False, default=0)

    added_by = Column(INT, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    edited_by = Column(INT, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    _last_date_used = Column("last_date_used", UtcDateTime(), nullable=True, default=None)

    user = relationship(
        User,
        primaryjoin="User.id==CommandData.edited_by",
        foreign_keys="User.id",
        uselist=False,
        cascade="",
        lazy="noload",
        viewonly=True,
    )

    user2 = relationship(
        User,
        primaryjoin="User.id==CommandData.added_by",
        foreign_keys="User.id",
        uselist=False,
        cascade="",
        lazy="noload",
        viewonly=True,
    )

    def __init__(self, command_id: int, **options) -> None:
        self.command_id = command_id
        self.num_uses = 0
        self.added_by = None
        self.edited_by = None
        self._last_date_used = None

        self.set(**options)

    def set(self, **options: Any) -> None:
        self.num_uses = options.get("num_uses", self.num_uses)
        self.added_by = options.get("added_by", self.added_by)
        self.edited_by = options.get("edited_by", self.edited_by)
        self._last_date_used = options.get("last_date_used", self._last_date_used)

    @property
    def last_date_used(self) -> Optional[datetime.datetime]:
        if isinstance(self._last_date_used, datetime.datetime):
            return self._last_date_used

        return None

    @last_date_used.setter
    def last_date_used(self, value: Optional[datetime.datetime]) -> None:
        self._last_date_used = value

    def jsonify(self) -> Dict[str, Any]:
        return {
            "num_uses": self.num_uses,
            "added_by": self.added_by,
            "edited_by": self.edited_by,
            "last_date_used": self.last_date_used.isoformat() if self.last_date_used else None,
        }


class CommandExample(Base):
    __tablename__ = "command_example"

    id = Column(INT, primary_key=True)
    command_id = Column(INT, ForeignKey("command.id", ondelete="CASCADE"), nullable=False)
    title = Column(TEXT, nullable=False)
    chat = Column(TEXT, nullable=False)
    description = Column(TEXT, nullable=False)

    def __init__(self, command_id: Optional[int], title: str, chat: str = "", description: str = "") -> None:
        if command_id:
            self.command_id = command_id
        self.title = title
        self.chat = chat
        self.description = description
        self.chat_messages: List[Dict[str, Any]] = []

    @reconstructor
    def init_on_load(self) -> None:
        self.parse()

    def add_chat_message(self, type: str, message: str, user_from: str, user_to: Optional[str] = None) -> None:
        chat_message = {"source": {"type": type, "from": user_from, "to": user_to}, "message": message}
        self.chat_messages.append(chat_message)

    def parse(self) -> CommandExample:
        self.chat_messages = []
        for line in self.chat.split("\n"):
            users, message = line.split(":", 1)
            if ">" in users:
                user_from, user_to = users.split(">", 1)
                self.add_chat_message("whisper", message, user_from, user_to=user_to)
            else:
                self.add_chat_message("say", message, users)
        return self

    def jsonify(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "command_id": self.command_id,
            "title": self.title,
            "description": self.description,
            "messages": self.chat_messages,
        }


class Command(Base):
    __tablename__ = "command"

    id = Column(INT, primary_key=True)
    level = Column(INT, nullable=False, default=100)
    action_json = Column("action", TEXT, nullable=False)
    extra_extra_args = Column("extra_args", TEXT)
    command = Column(TEXT, nullable=False)
    description = Column(TEXT, nullable=True)
    delay_all = Column(INT, nullable=False, default=5)
    delay_user = Column(INT, nullable=False, default=15)
    enabled = Column(BOOLEAN, nullable=False, default=True)
    cost = Column(INT, nullable=False, default=0)
    tokens_cost = Column(INT, nullable=False, default=0, server_default="0")
    can_execute_with_whisper = Column(BOOLEAN)
    sub_only = Column(BOOLEAN, nullable=False, default=False)
    mod_only = Column(BOOLEAN, nullable=False, default=False)
    run_through_banphrases = Column(BOOLEAN, nullable=False, default=False, server_default="0")
    use_global_cd = Column(BOOLEAN, nullable=False, default=False, server_default="0")
    long_description = ""

    data = relationship(CommandData, uselist=False, cascade="", lazy="joined")
    examples = relationship(CommandExample, uselist=True, cascade="", lazy="noload")

    MIN_WHISPER_LEVEL = 420
    BYPASS_DELAY_LEVEL = 2000
    BYPASS_SUB_ONLY_LEVEL = 500
    BYPASS_MOD_ONLY_LEVEL = 500

    DEFAULT_CD_ALL = 5
    DEFAULT_CD_USER = 15
    DEFAULT_LEVEL = 100

    notify_on_error = False

    def __init__(self, **options) -> None:
        self.id = options.get("id", None)

        self.level = Command.DEFAULT_LEVEL
        self.action: Optional[BaseAction] = None
        self.extra_args = {"command": self}
        self.delay_all = Command.DEFAULT_CD_ALL
        self.delay_user = Command.DEFAULT_CD_USER
        self.description = None
        self.enabled = True
        self.type = "?"  # XXX: What is this?
        self.cost = 0
        self.tokens_cost = 0
        self.can_execute_with_whisper = False
        self.sub_only = False
        self.mod_only = False
        self.run_through_banphrases = False
        self.use_global_cd = False

        self.last_run = 0
        self.last_run_by_user: Dict[str, datetime.datetime] = {}

        self.run_in_thread = False
        self.notify_on_error = False

        self.set(**options)

    def set(self, **options: Any) -> None:
        self.level = options.get("level", self.level)
        action_dict = options.get("action", None)
        if action_dict:
            self.action_json = json.dumps(action_dict)
            self.action = ActionParser.parse(str_data=self.action_json, command=self.command)
        self.command = options.get("command", self.command)
        self.description = options.get("description", self.description)
        self.delay_all = options.get("delay_all", self.delay_all)
        if self.delay_all < 0:
            self.delay_all = 0
        self.delay_user = options.get("delay_user", self.delay_user)
        if self.delay_user < 0:
            self.delay_user = 0
        self.enabled = options.get("enabled", self.enabled)
        self.cost = options.get("cost", self.cost)
        if self.cost < 0:
            self.cost = 0
        self.tokens_cost = options.get("tokens_cost", self.tokens_cost)
        if self.tokens_cost < 0:
            self.tokens_cost = 0
        self.can_execute_with_whisper = options.get("can_execute_with_whisper", self.can_execute_with_whisper)
        self.sub_only = options.get("sub_only", self.sub_only)
        self.mod_only = options.get("mod_only", self.mod_only)
        self.run_through_banphrases = options.get("run_through_banphrases", self.run_through_banphrases)
        self.examples = options.get("examples", self.examples)
        self.run_in_thread = options.get("run_in_thread", self.run_in_thread)
        self.notify_on_error = options.get("notify_on_error", self.notify_on_error)
        self.use_global_cd = options.get("use_global_cd", self.use_global_cd)

    def __str__(self):
        return f"Command(!{self.command})"

    @reconstructor
    def init_on_load(self) -> None:
        self.last_run = 0
        self.last_run_by_user = {}
        self.extra_args = {"command": self}
        self.action = ActionParser.parse(self.action_json, command=self.command)
        self.run_in_thread = False
        if self.extra_extra_args:
            try:
                self.extra_args.update(json.loads(self.extra_extra_args))
            except:
                log.exception(
                    f"Unhandled exception caught while loading Command extra arguments ({self.extra_extra_args})"
                )

    @classmethod
    def from_json(cls, json_object) -> Command:
        cmd = cls()
        if "level" in json_object:
            cmd.level = json_object["level"]
        cmd.action = ActionParser.parse(dict_data=json_object["action"], command=cmd.command)
        return cmd

    @classmethod
    def dispatch_command(cls, cb: Any, **options: Any) -> Command:
        cmd = cls(**options)
        cmd.action = ActionParser.parse('{"type": "func", "cb": "' + cb + '"}', command=cmd.command)
        return cmd

    @classmethod
    def raw_command(cls, cb, **options):
        cmd = cls(**options)
        try:
            cmd.action = RawFuncAction(cb)
        except:
            log.exception("Uncaught exception in Command.raw_command. catch the following exception manually!")
            cmd.enabled = False
        return cmd

    @classmethod
    def pajbot_command(cls, bot: Optional[Bot], method_name: str, level: int = 1000, **options) -> Command:
        cmd = cls(**options)
        cmd.level = level
        cmd.description = options.get("description", None)
        cmd.can_execute_with_whisper = True
        try:
            if bot:
                cmd.action = RawFuncAction(getattr(bot, method_name))
        except:
            pass
        return cmd

    @classmethod
    def multiaction_command(cls, default=None, fallback=None, **options) -> Command:
        from pajbot.models.action import MultiAction

        cmd = cls(**options)
        cmd.action = MultiAction.ready_built(options.get("commands"), default=default, fallback=fallback)
        return cmd

    def load_args(self, level: int, action) -> None:
        self.level = level
        self.action = action

    def is_enabled(self) -> bool:
        return self.enabled == 1 and self.action is not None

    def can_run_command(self, source, whisper) -> bool:
        if source.level < self.level:
            # User does not have a high enough power level to run this command
            return False

        if (
            whisper
            and self.can_execute_with_whisper is False
            and source.level < Command.MIN_WHISPER_LEVEL
            and source.moderator is False
        ):
            # This user cannot execute the command through a whisper
            return False

        if (
            self.sub_only
            and source.subscriber is False
            and source.level < Command.BYPASS_SUB_ONLY_LEVEL
            and source.moderator is False
        ):
            # User is not a sub or a moderator, and cannot use the command.
            return False

        if self.mod_only and source.moderator is False and source.level < Command.BYPASS_MOD_ONLY_LEVEL:
            # User is not a twitch moderator, or a bot moderator
            return False

        return True

    def run(self, bot, source, message, event={}, args={}, whisper=False):
        if self.action is None:
            log.warning("This command is not available.")
            return False

        if not self.can_run_command(source, whisper):
            return False

        cd_modifier = 0.2 if source.level >= 500 or source.moderator is True else 1.0

        cur_time = pajbot.utils.now().timestamp()
        time_since_last_run = (cur_time - self.last_run) / cd_modifier

        if time_since_last_run < self.delay_all and source.level < Command.BYPASS_DELAY_LEVEL:
            log.debug(f"Command was run {time_since_last_run:.2f} seconds ago, waiting...")
            return False

        time_since_last_run_user = (cur_time - self.last_run_by_user.get(source.id, 0)) / cd_modifier

        if time_since_last_run_user < self.delay_user and source.level < Command.BYPASS_DELAY_LEVEL:
            log.debug(f"{source} ran command {time_since_last_run_user:.2f} seconds ago, waiting...")
            return False

        if self.cost > 0 and not source.can_afford(self.cost):
            if self.notify_on_error:
                bot.whisper(
                    source,
                    f"You do not have the required {self.cost} points to execute this command. (You have {source.points} points)",
                )
            # User does not have enough points to use the command
            return False

        if self.tokens_cost > 0 and not source.can_afford_with_tokens(self.tokens_cost):
            if self.notify_on_error:
                bot.whisper(
                    source,
                    f"You do not have the required {self.tokens_cost} tokens to execute this command. (You have {source.tokens} tokens)",
                )
            # User does not have enough tokens to use the command
            return False

        if self.use_global_cd and source.level < Command.BYPASS_DELAY_LEVEL:
            # Command has chosen to respect the Global command cooldown module
            global_cd_module = bot.module_manager["global_command_cooldown"]
            if global_cd_module:
                # The global command cooldown module is enabled
                if not global_cd_module.run_command():
                    # The global command cooldown is currently active, command will be available to run when it has expired
                    return False

        args.update(self.extra_args)
        if self.run_in_thread:
            log.debug(f"Running {self} in a thread")
            ScheduleManager.execute_now(self.run_action, args=[bot, source, message, event, args])
        else:
            self.run_action(bot, source, message, event, args)

        return True

    def run_action(self, bot, source, message, event, args):
        cur_time = pajbot.utils.now().timestamp()
        with source.spend_currency_context(self.cost, self.tokens_cost):
            ret = self.action.run(bot, source, message, event, args)
            if ret is False:
                raise FailedCommand("return currency")

            # Only spend points/tokens, and increment num_uses if the action succeded
            if self.data is not None:
                self.data.num_uses += 1
                self.data.last_date_used = pajbot.utils.now()

            # TODO: Will this be an issue?
            self.last_run = cur_time
            self.last_run_by_user[source.id] = cur_time

    def jsonify(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "id": self.id,
            "level": self.level,
            "description": self.description,
            "long_description": self.long_description,
            "cd_all": self.delay_all,
            "cd_user": self.delay_user,
            "enabled": self.enabled,
            "cost": self.cost,
            "tokens_cost": self.tokens_cost,
            "can_execute_with_whisper": self.can_execute_with_whisper,
            "sub_only": self.sub_only,
            "mod_only": self.mod_only,
            "data": None,
        }

        if self.data:
            payload["data"] = self.data.jsonify()
        else:
            payload["data"] = None

        return payload


class WebCommand:
    def __init__(self, alias: str, command: Command) -> None:
        self._command = command

        self.command: str = alias

        if self._command.command:
            self.command = self._command.command

        self.main_alias = f"!{self.command}"

        self.parsed_description = ""
        self.json_description: Optional[Dict[str, Any]] = None
        self.resolve_string: Optional[str] = None

    @property
    def description(self) -> Optional[str]:
        return self._command.description

    @property
    def action(self) -> Optional[BaseAction]:
        return self._command.action

    @property
    def level(self) -> int:
        return self._command.level

    @property
    def mod_only(self) -> bool:
        return self._command.mod_only

    @property
    def cost(self) -> int:
        return self._command.cost

    @property
    def data(self) -> Optional[CommandData]:
        return self._command.data

    @property
    def id(self):
        return self._command.id

    def autogenerate_examples(self) -> List[CommandExample]:
        if self._command.examples:
            # Command has a 'hard-coded' list of examples, return it!
            return self._command.examples

        if (
            self.id is not None
            and self.action
            and self.action.type == "message"
            and isinstance(self.action, MessageAction)
            and self.main_alias
        ):
            examples = []

            example = CommandExample(self.id, "Default usage")
            subtype = self.action.subtype if self.action.subtype != "reply" else "say"
            example.add_chat_message("say", self.main_alias, "user")
            clean_response = Substitution.urlfetch_substitution_regex.sub("(urlfetch)", self.action.response)

            if subtype in ("say", "me"):
                example.add_chat_message(subtype, clean_response, "bot")
            elif subtype == "whisper":
                example.add_chat_message(subtype, clean_response, "bot", "user")
            examples.append(example)

            if self._command.can_execute_with_whisper is True:
                example = CommandExample(self.id, "Default usage through whisper")
                subtype = self.action.subtype if self.action.subtype != "reply" else "say"
                example.add_chat_message("whisper", self.main_alias, "user", "bot")
                if subtype in ("say", "me"):
                    example.add_chat_message(subtype, clean_response, "bot")
                elif subtype == "whisper":
                    example.add_chat_message(subtype, clean_response, "bot", "user")
                examples.append(example)
            return examples

        return []

    def jsonify(self) -> Dict[str, Any]:
        b = self._command.jsonify()

        return {
            **b,
            "json_description": self.json_description,
            "parsed_description": self.parsed_description,
            "main_alias": self.main_alias,
            "resolve_string": self.resolve_string,
            "aliases": self.command.split("|"),
            "examples": [example.jsonify() for example in self.autogenerate_examples()],
        }
