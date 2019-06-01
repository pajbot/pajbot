import logging

from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.modules.basic import BasicCommandsModule
from pajbot.modules.linkchecker import find_unique_urls

log = logging.getLogger(__name__)


class AbCommandModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "!ab"
    DESCRIPTION = "Inject an emote inbetween each letter/word in message"
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
    def ab(**options):
        bot = options["bot"]
        message = options["message"]
        source = options["source"]

        if message:
            """ check if there is a link in the message """
            check_message = find_unique_urls(bot.url_regex, message)
            if check_message == set():
                msg_parts = message.split(" ")
                if len(msg_parts) >= 2:
                    outer_str = msg_parts[0]
                    inner_str = " {} ".format(outer_str).join(msg_parts[1:] if len(msg_parts) >= 3 else msg_parts[1])
                    bot.say("{0}, {1} {2} {1}".format(source.username_raw, outer_str, inner_str))
                    return True

        return

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
