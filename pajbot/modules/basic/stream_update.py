import logging

from requests import HTTPError

from pajbot.managers.adminlog import AdminLogManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.modules.basic import BasicCommandsModule

log = logging.getLogger(__name__)


class StreamUpdateModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Stream Update Commands"
    DESCRIPTION = "Update the stream game and title using commands from chat"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = True
    PARENT_MODULE = BasicCommandsModule
    SETTINGS = [
        ModuleSetting(
            key="setgame_trigger",
            label="Set game trigger (e.g. setgame)",
            type="text",
            required=True,
            placeholder="Command (no !)",
            default="setgame",
            constraints={"min_str_len": 1, "max_str_len": 30},
        ),
        ModuleSetting(
            key="settitle_trigger",
            label="Set title trigger (e.g. settitle)",
            type="text",
            required=True,
            placeholder="Trigger (no !)",
            default="settitle",
            constraints={"min_str_len": 1, "max_str_len": 30},
        ),
        ModuleSetting(
            key="level",
            label="Level required to use the commands",
            type="number",
            required=True,
            placeholder="",
            default=500,
            constraints={"min_value": 250, "max_value": 2000},
        ),
    ]

    def generic_update(self, bot, source, message, field, api_fn):
        if not message:
            bot.say(f"You must specify a {field} to update to!")
            return

        if "channel_editor" in bot.streamer_access_token_manager.token.scope:
            api_fn(self.bot.streamer_user_id, message, authorization=bot.streamer_access_token_manager)
        else:
            try:
                api_fn(self.bot.streamer_user_id, message, authorization=bot.bot_token_manager)
            except HTTPError as e:
                if e.response.status_code == 401:
                    bot.say(
                        f"Error: Neither the streamer nor the bot token grants permission to update the {field}. The streamer needs to be re-authenticated to fix this problem."
                    )
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
        setgame_trigger = self.settings["setgame_trigger"].lower().replace("!", "").replace(" ", "")
        self.commands[setgame_trigger] = Command.raw_command(
            self.update_game,
            level=self.settings["level"],
            description="Update the stream's game",
            examples=[
                CommandExample(
                    None,
                    'Update the game to "World of Warcraft"',
                    chat=f"user:!{setgame_trigger} World of Warcraft\n"
                    'bot>user:pajlada updated the game to "World of Warcraft"',
                ).parse()
            ],
        )

        settitle_trigger = self.settings["settitle_trigger"].lower().replace("!", "").replace(" ", "")
        self.commands[settitle_trigger] = Command.raw_command(
            self.update_title,
            level=self.settings["level"],
            description="Update the stream's title",
            examples=[
                CommandExample(
                    None,
                    'Update the title to "Games and shit"',
                    chat=f"user:!{settitle_trigger} Games and shit\n"
                    'bot>user:pajlada updated the title to "Games and shit"',
                ).parse()
            ],
        )
