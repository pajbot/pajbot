import logging

from pajbot.models.command import Command, CommandExample
from pajbot.modules import BaseModule, ModuleSetting
from pajbot.modules.basic import BasicCommandsModule

log = logging.getLogger(__name__)


class TwitterModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Twitter"
    DESCRIPTION = "Enable !twitterfollow/!twitterunfollow command usage"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = True
    PARENT_MODULE = BasicCommandsModule
    SETTINGS = [
        ModuleSetting(
            key="level",
            label="Minimum level required to use commands",
            type="number",
            required=True,
            placeholder="",
            default=1000,
            constraints={"min_value": 1000}
        ),
    ]

    @staticmethod
    def twitter_follow(bot, source, message, event, args):
        if message:
            username = message.split(" ")[0].strip().lower()
            if bot.twitter_manager.follow_user(username):
                bot.whisper(source, f"Now following {username}")
            else:
                bot.whisper(
                    source,
                    f"An error occured while attempting to follow {username}, perhaps we are already following this person?",
                )

    @staticmethod
    def twitter_unfollow(bot, source, message, event, args):
        if message:
            username = message.split(" ")[0].strip().lower()
            if bot.twitter_manager.unfollow_user(username):
                bot.whisper(source, f"No longer following {username}")
            else:
                bot.whisper(
                    source,
                    f"An error occured while attempting to unfollow {username}, perhaps we are not following this person?",
                )

    def load_commands(self, **options):
        self.commands["twitterfollow"] = Command.raw_command(
            self.twitter_follow,
            level=self.settings["level"],
            description="Start listening for tweets for the given user",
            examples=[
                CommandExample(
                    None,
                    "Default usage",
                    chat="user:!twitterfollow forsen\n" "bot>user:Now following Forsen",
                    description="Follow Forsen on twitter so new tweets are output in chat.",
                ).parse()
            ],
        )

        self.commands["twitterunfollow"] = Command.raw_command(
            self.twitter_unfollow,
            level=self.settings["level"],
            description="Stop listening for tweets for the given user",
            examples=[
                CommandExample(
                    None,
                    "Default usage",
                    chat="user:!twitterunfollow forsen\n" "bot>user:No longer following Forsen",
                    description="Stop automatically printing tweets from Forsen",
                ).parse()
            ],
        )
