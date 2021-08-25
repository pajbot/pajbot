from typing import Dict, Optional, Any

import logging

from requests.exceptions import HTTPError
from pajbot.managers.adminlog import AdminLogManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.modules.basic import BasicCommandsModule
from pajbot.apiwrappers.twitch.helix import TwitchGame
from pajbot.bot import Bot

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
            key="allow_mods_change_title",
            label="Allow all moderators to change the title (ignores the level setting)",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="allow_mods_change_game",
            label="Allow all moderators to change the game (ignores the level setting)",
            type="boolean",
            required=True,
            default=False,
        ),
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

    def update_game(self, bot, source, message, **rest) -> Any:
        if "user:edit:broadcast" not in bot.streamer_access_token_manager.token.scope:
            bot.say(
                "Error: The streamer must grant permissions to update the game. The streamer needs to be re-authenticated to fix this problem."
            )
            return

        if not message:
            bot.say("You must specify a game to update to!")
            return

        # Resolve game name to game ID
        game: Optional[TwitchGame] = self.bot.twitch_helix_api.get_game_by_game_name(message)
        if not game:
            bot.say(f"Unable to find a game with the name '{message}'")
            return

        try:
            self.bot.twitch_helix_api.modify_channel_information(
                self.bot.streamer_user_id,
                authorization=bot.streamer_access_token_manager,
                body={"game_id": game.id},
            )
        except HTTPError as e:
            if e.response.status_code == 500:
                bot.say(f"{source}, Failed to update game! Please try again.")
                return

        log_msg = f'{source} updated the game to "{message}"'
        bot.say(log_msg)
        AdminLogManager.add_entry("Game set", source, log_msg)

    def update_title(self, bot, source, message, **rest) -> Any:
        if "user:edit:broadcast" not in bot.streamer_access_token_manager.token.scope:
            bot.say(
                "Error: The streamer must grant permissions to update the game. The streamer needs to be re-authenticated to fix this problem."
            )
            return

        if not message:
            bot.say("You must specify a title to update to!")
            return

        try:
            self.bot.twitch_helix_api.modify_channel_information(
                self.bot.streamer_user_id,
                authorization=bot.streamer_access_token_manager,
                body={"title": message},
            )
        except HTTPError as e:
            if e.response.status_code == 400:
                if e.response.reason == "Status contains banned words.":
                    bot.say(f"{source}, Title contained banned words. Please remove the banned words and try again.")
                    return

            if e.response.status_code == 500:
                bot.say(f"{source}, Failed to update the title! Please try again.")
                return

        log_msg = f'{source} updated the title to "{message}"'
        bot.say(log_msg)
        AdminLogManager.add_entry("Title set", source, log_msg)

    def load_commands(self, **options):
        setgame_trigger = self.settings["setgame_trigger"].lower().replace("!", "").replace(" ", "")
        if self.settings["allow_mods_change_game"] is True:
            self.commands[setgame_trigger] = Command.raw_command(
                self.update_game,
                level=100,
                mod_only=True,
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
        else:
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
        if self.settings["allow_mods_change_title"] is True:
            self.commands[settitle_trigger] = Command.raw_command(
                self.update_title,
                level=100,
                mod_only=True,
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
        else:
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
