import datetime
import logging

from pajbot import utils
from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.models.command import Command, CommandExample
from pajbot.models.user import User
from pajbot.modules import BaseModule, ModuleSetting

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
        ModuleSetting(
            key="message_to_timeouter",
            label="Message sent to timeouter. Leave empty to disable message. | Available arguments: {victim}, {cost}, {duration}",
            type="text",
            required=False,
            placeholder="You just used {cost} points to timeout {victim} for {duration} seconds.",
            default="You just used {cost} points to timeout {victim} for {duration} seconds.",
            constraints={"max_str_len": 300},
        ),
        ModuleSetting(
            key="message_to_additional_timeouter",
            label="Message sent to additional timeouter. Leave empty to disable message. | Available arguments: {victim}, {cost}, {duration}",
            type="text",
            required=False,
            placeholder="You just used {cost} points to timeout {victim} for an additional {duration} seconds.",
            default="You just used {cost} points to timeout {victim} for an additional {duration} seconds.",
            constraints={"max_str_len": 300},
        ),
        ModuleSetting(
            key="message_to_victim",
            label="Message sent to victim when timed out. Leave empty to disable message. | Available arguments: {source}, {duration}",
            type="text",
            required=False,
            placeholder="{source} just timed you out for {duration} seconds LUL",
            default="{source} just timed you out for {duration} seconds LUL",
            constraints={"max_str_len": 300},
        ),
        ModuleSetting(
            key="additional_message_to_victim",
            label="Message sent to victim when more time is added to the victim's timeout. Leave empty to disable message. | Available arguments: {source}, {duration}",
            type="text",
            required=False,
            placeholder="{source} just timed you out for an additional {duration} seconds LUL",
            default="{source} just timed you out for an additional {duration} seconds LUL",
            constraints={"max_str_len": 300},
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
                bot.send_message(source, "This user does not exist FailFish", method="whisper")
                return False

            if victim.last_active is None or (utils.now() - victim.last_active) > datetime.timedelta(minutes=10):
                bot.send_message(
                    source,
                    "This user has not been active in chat within the last 10 minutes FailFish",
                    method="whisper",
                )
                return False

            if victim.moderator is True:
                bot.send_message(
                    source,
                    "This person has mod privileges, timing out this person is not worth it FailFish",
                    method="whisper",
                )
                return False

            if victim.level >= self.settings["bypass_level"]:
                bot.send_message(
                    source,
                    "This person's user level is too high, you can't timeout this person FailFish",
                    method="whisper",
                )
                return False

            now = utils.now()
            if victim.timeout_end is not None and victim.timeout_end > now:
                victim.timeout_end += datetime.timedelta(seconds=_time)

                if self.settings["additional_message_to_victim"] != "":
                    bot.send_message(
                        victim,
                        self.get_phrase("additional_message_to_victim", source=source, duration=_time),
                        method="whisper",
                    )

                if self.settings["message_to_additional_timeouter"] != "":
                    bot.send_message(
                        source,
                        self.get_phrase("message_to_additional_timeouter", victim=victim, cost=_cost, duration=_time),
                        method="whisper",
                    )

                num_seconds = int((victim.timeout_end - now).total_seconds())
                bot.timeout(victim, num_seconds, reason=f"Timed out by {source}", once=True)
            else:
                if self.settings["message_to_timeouter"] != "":
                    bot.send_message(
                        source,
                        self.get_phrase("message_to_timeouter", victim=victim, cost=_cost, duration=_time),
                        method="whisper",
                    )

                if self.settings["message_to_victim"] != "":
                    bot.send_message(
                        victim,
                        self.get_phrase("message_to_victim", source=source, duration=_time),
                        method="whisper",
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
        payload = {"victim": "karl_kons", "cost": self.settings["cost"], "duration": self.settings["timeout_length"]}

        self.commands[self.settings["command_name"].lower().replace("!", "").replace(" ", "")] = Command.raw_command(
            self.paid_timeout,
            cost=self.settings["cost"],
            examples=[
                CommandExample(
                    None,
                    f"Timeout someone for {self.settings['timeout_length']} seconds",
                    chat=f"user:!{self.settings['command_name']} karl_kons\nbot>user: {self.get_phrase('message_to_additional_timeouter', **payload)}",
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
                        chat=f"user:!{self.settings['command_name2']} karl_kons\nbot>user: {self.get_phrase('message_to_additional_timeouter', **payload)}",
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
