import datetime
import logging

from pajbot import utils
from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.models.user import User
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


class PaidTimeoutModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Paid Timeout"
    DESCRIPTION = "Allows user to time out other users with points"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="command_name",
            label="Command name (i.e. $timeout)",
            type="text",
            required=True,
            placeholder="Command name (no !)",
            default="timeout",
            constraints={"min_str_len": 2, "max_str_len": 15},
        ),
        ModuleSetting(
            key="timeout_length",
            label="Timeout length",
            type="number",
            required=True,
            placeholder="Timeout length in seconds",
            default=60,
            constraints={"min_value": 1, "max_value": 1209600},
        ),
        ModuleSetting(
            key="cost",
            label="Point cost",
            type="number",
            required=True,
            placeholder="Point cost",
            default=400,
            constraints={"min_value": 1, "max_value": 1000000},
        ),
        ModuleSetting(
            key="second_command", label="Enable a second timeout command", type="boolean", required=True, default=False
        ),
        ModuleSetting(
            key="command_name2",
            label="Command name (i.e. $timeout5)",
            type="text",
            required=True,
            placeholder="Command name (no !)",
            default="timeout5",
            constraints={"min_str_len": 2, "max_str_len": 15},
        ),
        ModuleSetting(
            key="timeout_length2",
            label="Timeout length for the second timeout command",
            type="number",
            required=True,
            placeholder="Timeout length in seconds",
            default=60,
            constraints={"min_value": 1, "max_value": 1209600},
        ),
        ModuleSetting(
            key="cost2",
            label="Point cost for the second timeout command",
            type="number",
            required=True,
            placeholder="Point cost",
            default=400,
            constraints={"min_value": 1, "max_value": 1000000},
        ),
        ModuleSetting(
            key="bypass_level",
            label="Level to bypass module (people with this level or above are immune to paid timeouts)",
            type="number",
            required=True,
            placeholder="",
            default=500,
            constraints={"min_value": 100, "max_value": 1000},
        ),
        ModuleSetting(
            key="show_on_clr", label="Show timeouts on the clr overlay", type="boolean", required=True, default=True
        ),
    ]

    def base_paid_timeout(self, bot, source, message, _time, _cost):
        if message is None or len(message) == 0:
            return False

        target = message.split(" ")[0]
        if len(target) < 2:
            return False

        with DBManager.create_session_scope() as db_session:
            victim = User.find_by_user_input(db_session, target)

            if victim is None:
                bot.whisper(source, "This user does not exist FailFish")
                return False

            if victim.last_active is None or (utils.now() - victim.last_active) > datetime.timedelta(minutes=10):
                bot.whisper(source, "This user has not been active in chat within the last 10 minutes.")
                return False

            if victim.moderator is True:
                bot.whisper(source, "This person has mod privileges, timeouting this person is not worth it.")
                return False

            if victim.level >= self.settings["bypass_level"]:
                bot.whisper(source, "This person's user level is too high, you can't timeout this person.")
                return False

            now = utils.now()
            if victim.timeout_end is not None and victim.timeout_end > now:
                victim.timeout_end += datetime.timedelta(seconds=_time)
                bot.whisper(victim, f"{victim}, you were timed out for an additional {_time} seconds by {source}")
                bot.whisper(
                    source, f"You just used {_cost} points to time out {victim} for an additional {_time} seconds."
                )
                num_seconds = int((victim.timeout_end - now).total_seconds())
                bot.timeout(victim, num_seconds, reason=f"Timed out by {source}", once=True)
            else:
                bot.whisper(source, f"You just used {_cost} points to time out {victim} for {_time} seconds.")
                bot.whisper(
                    victim,
                    f"{source} just timed you out for {_time} seconds LUL",
                )
                bot.timeout(victim, _time, reason=f"Timed out by {source}", once=True)
                victim.timeout_end = now + datetime.timedelta(seconds=_time)

            if self.settings["show_on_clr"]:
                payload = {"user": source.name, "victim": victim.name}
                bot.websocket_manager.emit("timeout", payload)

            HandlerManager.trigger("on_paid_timeout", source=source, victim=victim, cost=_cost, stop_on_false=False)

    def paid_timeout(self, bot, source, message, **rest):
        _time = self.settings["timeout_length"]
        _cost = self.settings["cost"]

        return self.base_paid_timeout(bot, source, message, _time, _cost)

    def paid_timeout2(self, bot, source, message, **rest):
        _time = self.settings["timeout_length2"]
        _cost = self.settings["cost2"]

        return self.base_paid_timeout(bot, source, message, _time, _cost)

    def load_commands(self, **options):
        self.commands[self.settings["command_name"].lower().replace("!", "").replace(" ", "")] = Command.raw_command(
            self.paid_timeout,
            cost=self.settings["cost"],
            examples=[
                CommandExample(
                    None,
                    f"Timeout someone for {self.settings['timeout_length']} seconds",
                    chat=f"user:!{self.settings['command_name']} paja\nbot>user: You just used {self.settings['cost']} points to time out paja for an additional {self.settings['timeout_length']} seconds.",
                    description="",
                ).parse()
            ],
        )
        if self.settings["second_command"]:
            self.commands[
                self.settings["command_name2"].lower().replace("!", "").replace(" ", "")
            ] = Command.raw_command(
                self.paid_timeout2,
                cost=self.settings["cost2"],
                examples=[
                    CommandExample(
                        None,
                        f"Timeout someone for {self.settings['timeout_length2']} seconds",
                        chat=f"user:!{self.settings['command_name2']} paja\nbot>user: You just used {self.settings['cost2']} points to time out paja for an additional {self.settings['timeout_length2']} seconds.",
                        description="",
                    ).parse()
                ],
            )

    def on_message(self, source, whisper, **rest):
        if whisper:
            return

        # If a user types when timed out, we assume he's been unbanned for a good reason and remove his flag.
        source.timed_out = False

    def enable(self, bot):
        if bot:
            HandlerManager.add_handler("on_message", self.on_message)

    def disable(self, bot):
        if bot:
            HandlerManager.remove_handler("on_message", self.on_message)
