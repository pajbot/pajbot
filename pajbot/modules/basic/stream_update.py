import logging

from requests import HTTPError

from pajbot.managers.adminlog import AdminLogManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules.basic import BasicCommandsModule

log = logging.getLogger(__name__)


class StreamUpdateModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Stream Update commands"
    DESCRIPTION = "Update the stream game and title using commands from chat"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = True
    PARENT_MODULE = BasicCommandsModule
    SETTINGS = []

    def generic_update(self, bot, source, message, field, api_fn):
        if not message:
            bot.say(f"You must specify a {field} to update to!")
            return

        try:
            api_fn(self.bot.streamer_user_id, message, authorization=bot.bot_token_manager)
        except HTTPError as e:
            if e.response.status_code == 401:
                bot.say(f"Error (bot operator): The bot needs to be re-authenticated to be able to update the {field}.")
                return
            elif e.response.status_code == 403:
                bot.say(f"Error: The bot is not a channel editor and was not able to update the {field}.")
                return
            else:
                raise e

        log_msg = f'{source} updated the {field} to "{message}"'
        bot.say(log_msg)
        AdminLogManager.add_entry(f"{field.capitalize()} set", source, log_msg)

    def update_game(self, bot, source, message, **rest):
        self.generic_update(bot, source, message, "game", self.bot.twitch_v5_api.set_game)

    def update_title(self, bot, source, message, **rest):
        self.generic_update(bot, source, message, "title", self.bot.twitch_v5_api.set_title)

    def load_commands(self, **options):
        self.commands["setgame"] = Command.raw_command(
            self.update_game,
            level=500,
            description="Update the stream's game",
            examples=[
                CommandExample(
                    None,
                    'Update the game to "World of Warcraft"',
                    chat=f"user:{bot.prefix}setgame World of Warcraft\n"
                    'bot>user:pajlada updated the game to "World of Warcraft"',
                ).parse()
            ],
        )

        self.commands["settitle"] = Command.raw_command(
            self.update_title,
            level=500,
            description="Update the stream's title",
            examples=[
                CommandExample(
                    None,
                    'Update the title to "Games and shit"',
                    chat=f"user:{bot.prefix}settitle Games and shit\n"
                    'bot>user:pajlada updated the title to "Games and shit"',
                ).parse()
            ],
        )
