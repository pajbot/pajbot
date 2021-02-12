from typing import Dict, Optional, Any

import logging

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

    def generic_update(self, bot: Bot, source, message: str, field: str, extra_args: Dict[str, str]) -> None:
        if not message:
            bot.say(f"You must specify a {field} to update to!")
            return

        if (
            "user:edit:broadcast" not in bot.streamer_access_token_manager.token.scope
            or not self.bot.twitch_helix_api.modify_channel_information(
                self.bot.streamer_user_id,
                authorization=bot.streamer_access_token_manager,
                **extra_args,
            )
        ):
            bot.say(
                "Error: The streamer grants permission to update the game. The streamer needs to be re-authenticated to fix this problem."
            )
            return

        log_msg = f'{source} updated the {field} to "{message}"'
        bot.say(log_msg)
        AdminLogManager.add_entry(f"{field.capitalize()} set", source, log_msg)

    def update_game(self, bot: Bot, source, message, **rest) -> Any:
        if not message:
            bot.say("You must specify a game to update to!")
            return

        # Resolve game name to game ID
        game: Optional[TwitchGame] = self.bot.twitch_helix_api.get_game_by_game_name(message)
        if not game:
            bot.say(f"Unable to find a game with the name '{message}'")
            return

        return self.generic_update(bot, source, message, "game", {"game_id": game.id})

    def update_title(self, bot, source, message, **rest) -> Any:
        if not message:
            bot.say("You must specify a title to update to!")
            return

        return self.generic_update(bot, source, message, "title", {"title": message})

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
