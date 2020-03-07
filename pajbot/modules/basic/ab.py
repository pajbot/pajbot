import logging

from pajbot.bot import URL_REGEX
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.modules.basic import BasicCommandsModule
from pajbot.modules.linkchecker import find_unique_urls

log = logging.getLogger(__name__)


class AbCommandModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Add Between"
    DESCRIPTION = "Inject an emote inbetween each letter/word in message via the !ab command"
    CATEGORY = "Feature"
    PARENT_MODULE = BasicCommandsModule
    SETTINGS = [
        ModuleSetting(
            key="level",
            label="minimum level (make sure people don't abuse this command)",
            type="number",
            required=True,
            placeholder="",
            default=250,
            constraints={"min_value": 100, "max_value": 2000},
        ),
        ModuleSetting(
            key="global_cd",
            label="Global cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=15,
            constraints={"min_value": 0, "max_value": 240},
        ),
        ModuleSetting(
            key="user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=30,
            constraints={"min_value": 0, "max_value": 240},
        ),
    ]

    @staticmethod
    def ab(bot, source, message, **rest):
        if not message:
            return False

        # check if there is a link in the message
        check_message = find_unique_urls(URL_REGEX, message)
        if len(check_message) > 0:
            return False

        msg_parts = message.split(" ")
        if len(msg_parts) >= 2:
            outer_str = msg_parts[0]
            inner_str = f" {outer_str} ".join(msg_parts[1:] if len(msg_parts) >= 3 else msg_parts[1])
            bot.say(f"{source}, {outer_str} {inner_str} {outer_str}")

    def load_commands(self, **options):
        self.commands["ab"] = Command.raw_command(
            self.ab,
            delay_all=self.settings["global_cd"],
            delay_user=self.settings["user_cd"],
            level=self.settings["level"],
            description="Inject emote inbetween each letter/word in message",
            command="ab",
            examples=[
                CommandExample(
                    None,
                    "Inject emote inbetween each letter in message",
                    chat="user:!ab Keepo KEEPO\n" "bot:pajlada, Keepo K Keepo E Keepo E Keepo P Keepo O Keepo",
                    description="",
                ).parse(),
                CommandExample(
                    None,
                    "Inject emote inbetween each word in message",
                    chat="user:!ab Kreygasm NOW THATS WHAT I CALL MUSIC\n"
                    "bot:pajlada, Kreygasm NOW Kreygasm THATS Kreygasm WHAT Kreygasm I Kreygasm CALL Kreygasm MUSIC Kreygasm",
                    description="",
                ).parse(),
            ],
        )
        self.commands["abc"] = self.commands["ab"]
