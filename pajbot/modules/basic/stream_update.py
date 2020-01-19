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

    def game(self, bot, source, message, **rest):
        if not message or source.level < 500:
            data = bot.twitch_v5_api.get_stream_status(bot.streamer_user_id)
            game = data["game"]
            bot.say(f'@{source.username_raw} -> {bot.streamer} is currently playing "{game}"')
            return
        self.generic_update(bot, source, message, "game", self.bot.twitch_v5_api.set_game)

    def title(self, bot, source, message, **rest):
        if not message or source.level < 500:
            data = bot.twitch_v5_api.get_stream_status(bot.streamer_user_id)
            title = data["title"]
            bot.say(f'@{source.username_raw} -> The current title is "{title}"')
            return
        self.generic_update(bot, source, message, "title", self.bot.twitch_v5_api.set_title)

    def load_commands(self, **options):
        self.commands["game"] = Command.raw_command(
            self.game,
            level=100,
            description="Updates or Shows the stream's game",
            examples=[
                CommandExample(
                    None,
                    "Shows the game",
                    chat="user:!game\n" 'bot: @user -> $(tb:broadcaster) is currently playing "Dota 2"',
                ).parse(),
                CommandExample(
                    None,
                    'Update the game to "Dota 2"',
                    chat="user:!game Dota 2\n" 'bot: @user updated the game to "Dota 2"',
                ).parse(),
            ],
        )

        self.commands["title"] = Command.raw_command(
            self.title,
            level=100,
            description="Updates or Shows  the stream's title",
            examples=[
                CommandExample(
                    None, "Shows the title", chat="user:!title\n" 'bot: @user -> The current title is: $(tb:title)"',
                ).parse(),
                CommandExample(
                    None,
                    'Update the title to "Just A Title"',
                    chat="user:!title Just A Title\n" 'bot: @user updated the title to "Just A Title"',
                ).parse(),
            ],
        )
