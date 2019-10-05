import datetime
import logging

from pajbot import utils
from pajbot.managers.handler import HandlerManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
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
            constraints={"min_value": 1, "max_value": 3600},
        ),
        ModuleSetting(
            key="cost",
            label="Point cost",
            type="number",
            required=True,
            placeholder="Point cost",
            default=400,
            constraints={"min_value": 1, "max_value": 10000},
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
            constraints={"min_value": 1, "max_value": 3600},
        ),
        ModuleSetting(
            key="cost2",
            label="Point cost for the second timeout command",
            type="number",
            required=True,
            placeholder="Point cost",
            default=400,
            constraints={"min_value": 1, "max_value": 10000},
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

        with bot.users.find_context(target) as victim:
            if victim is None:
                bot.whisper(source.username, "This user does not exist FailFish")
                return False

            if victim.last_active is None or (utils.now() - victim._last_active).total_seconds() > 10 * 60:
                bot.whisper(source.username, "This user has not been active in chat within the last 10 minutes.")
                return False

            """
            if victim == source:
                bot.whisper(source.username, 'You can\'t timeout yourself FailFish')
                return False
                """

            if victim.moderator is True:
                bot.whisper(source.username, "This person has mod privileges, timeouting this person is not worth it.")
                return False

            if victim.level >= self.settings["bypass_level"]:
                bot.whisper(source.username, "This person's user level is too high, you can't timeout this person.")
                return False

            now = utils.now()
            if victim.timed_out is True and victim.timeout_end > now:
                victim.timeout_end += datetime.timedelta(seconds=_time)
                bot.whisper(
                    victim.username,
                    "{victim.username}, you were timed out for an additional {time} seconds by {source.username}".format(
                        victim=victim, source=source, time=_time
                    ),
                )
                bot.whisper(
                    source.username,
                    "You just used {0} points to time out {1} for an additional {2} seconds.".format(
                        _cost, victim.username, _time
                    ),
                )
                num_seconds = int((victim.timeout_end - now).total_seconds())
                bot._timeout(victim.username, num_seconds, reason="Timed out by {}".format(source.username_raw))
            else:
                bot.whisper(
                    source.username,
                    "You just used {0} points to time out {1} for {2} seconds.".format(_cost, victim.username, _time),
                )
                bot.whisper(
                    victim.username,
                    "{0} just timed you out for {1} seconds. /w {2} !$unbanme to unban yourself for points forsenMoney".format(
                        source.username, _time, bot.nickname
                    ),
                )
                bot._timeout(victim.username, _time, reason="Timed out by {}".format(source.username_raw))
                victim.timed_out = True
                victim.timeout_start = now
                victim.timeout_end = now + datetime.timedelta(seconds=_time)

            if self.settings["show_on_clr"]:
                payload = {"user": source.username, "victim": victim.username}
                bot.websocket_manager.emit("timeout", payload)

            HandlerManager.trigger("on_paid_timeout", source=source, victim=victim, cost=_cost, stop_on_false=False)

    def paid_timeout(self, **options):
        message = options["message"]
        bot = options["bot"]
        source = options["source"]

        _time = self.settings["timeout_length"]
        _cost = self.settings["cost"]

        return self.base_paid_timeout(bot, source, message, _time, _cost)

    def paid_timeout2(self, **options):
        message = options["message"]
        bot = options["bot"]
        source = options["source"]

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
                    "Timeout someone for {0} seconds".format(self.settings["timeout_length"]),
                    chat="user:!{0} paja\n"
                    "bot>user: You just used {1} points to time out paja for an additional {2} seconds.".format(
                        self.settings["command_name"], self.settings["cost"], self.settings["timeout_length"]
                    ),
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
                        "Timeout someone for {0} seconds".format(self.settings["timeout_length2"]),
                        chat="user:!{0} paja\n"
                        "bot>user: You just used {1} points to time out paja for an additional {2} seconds.".format(
                            self.settings["command_name2"], self.settings["cost2"], self.settings["timeout_length2"]
                        ),
                        description="",
                    ).parse()
                ],
            )

