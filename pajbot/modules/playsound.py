import json
import logging
import re
from argparse import ArgumentParser

from pajbot.managers.db import DBManager
from pajbot.models.playsound import Playsound
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.models.command import Command

log = logging.getLogger(__name__)


class PlaysoundModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Playsound"
    DESCRIPTION = "Play a sound on stream with !#playsound"
    CATEGORY = "Feature"
    SETTINGS = [
        ModuleSetting(
            key="point_cost",
            label="Point cost",
            type="number",
            required=True,
            placeholder="Point cost",
            default=200,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
        ModuleSetting(
            key="token_cost",
            label="Token cost",
            type="number",
            required=True,
            placeholder="Token cost",
            default=0,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
        ModuleSetting(
            key="global_cd",
            label="Global playsound cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=10,
            constraints={"min_value": 0, "max_value": 600},
        ),
        ModuleSetting(
            key="default_sample_cd",
            label="Default per-sample cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=30,
            constraints={"min_value": 0, "max_value": 600},
        ),
        ModuleSetting(
            key="user_cd",
            label="Per-user cooldown (seconds)",
            type="number",
            required=True,
            placeholder="",
            default=0,
            constraints={"min_value": 0, "max_value": 600},
        ),
        ModuleSetting(
            key="global_volume",
            label="Global volume (0-100)",
            type="number",
            required=True,
            placeholder="",
            default=40,
            constraints={"min_value": 0, "max_value": 100},
        ),
        ModuleSetting(key="sub_only", label="Subscribers only", type="boolean", required=True, default=False),
        ModuleSetting(key="can_whisper", label="Command can be whispered", type="boolean", required=True, default=True),
        ModuleSetting(
            key="confirmation_whisper",
            label="Send user a whisper when sound was successfully played",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="global_cd_whisper",
            label="Send user a whisper when playsounds are on global cooldown",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="user_cd_whisper",
            label="Send user a whisper when they hit the user-specific cooldown",
            type="boolean",
            required=True,
            default=True,
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)

        # this is for the "Test on stream" button on the admin page
        if bot:
            bot.socket_manager.add_handler("playsound.play", self.on_web_playsound)

        self.sample_cooldown = set()
        self.user_cooldown = set()
        self.global_cooldown = False

    # when a "Test on stream" is triggered via the Web UI.
    def on_web_playsound(self, data):
        # on playsound test triggered by the Web UI
        # this works even if the module is not enabled.
        playsound_name = data["name"]

        with DBManager.create_session_scope() as session:
            playsound = session.query(Playsound).filter(Playsound.name == playsound_name).one_or_none()

            if playsound is None:
                log.warning(f'Web UI tried to play invalid playsound "{playsound_name}". Ignoring.')
                return

            payload = {
                "link": playsound.link,
                "volume": int(round(playsound.volume * self.settings["global_volume"] / 100)),
            }

            log.debug(f"Playsound module is emitting payload: {json.dumps(payload)}")
            self.bot.websocket_manager.emit("play_sound", payload)

    def reset_global_cd(self):
        self.global_cooldown = False

    def play_sound(self, bot, source, message, **rest):
        if not message:
            return

        playsound_name = self.massage_name(message.split(" ")[0])

        with DBManager.create_session_scope() as session:
            # load playsound from the database
            playsound = session.query(Playsound).filter_by(name=playsound_name).one_or_none()

            if playsound is None:
                bot.whisper(
                    source,
                    f"The playsound you gave does not exist. Check out all the valid playsounds here: https://{self.bot.bot_domain}/playsounds",
                )
                return False

            if self.global_cooldown and source.level < Command.BYPASS_DELAY_LEVEL:
                if self.settings["global_cd_whisper"]:
                    bot.whisper(
                        source,
                        f"Another user played a sample too recently. Please try again after the global cooldown of {self.settings['global_cd']} seconds has run out.",
                    )
                return False

            if source.id in self.user_cooldown and source.level < Command.BYPASS_DELAY_LEVEL:
                if self.settings["user_cd_whisper"]:
                    bot.whisper(
                        source,
                        f"You can only play a sound every {self.settings['user_cd']} seconds. Please wait until the cooldown has run out.",
                    )
                return False

            cooldown = playsound.cooldown
            if cooldown is None:
                cooldown = self.settings["default_sample_cd"]

            if playsound_name in self.sample_cooldown and source.level < Command.BYPASS_DELAY_LEVEL:
                bot.whisper(
                    source,
                    f"The playsound {playsound.name} was played too recently. Please wait until its cooldown of {cooldown} seconds has run out.",
                )
                return False

            if not playsound.enabled:
                bot.whisper(
                    source,
                    f"The playsound you gave is disabled. Check out all the valid playsounds here: https://{self.bot.bot_domain}/playsounds",
                )
                return False

            payload = {
                "link": playsound.link,
                "volume": int(round(playsound.volume * self.settings["global_volume"] / 100)),
            }

            log.debug(f"Playsound module is emitting payload: {json.dumps(payload)}")
            bot.websocket_manager.emit("play_sound", payload)

            if self.settings["confirmation_whisper"]:
                bot.whisper(source, f"Successfully played the sound {playsound_name} on stream!")

            self.global_cooldown = True
            self.user_cooldown.add(source.id)
            self.sample_cooldown.add(playsound.name)
            bot.execute_delayed(cooldown, self.sample_cooldown.remove, playsound.name)
            bot.execute_delayed(self.settings["user_cd"], self.user_cooldown.remove, source.id)
            bot.execute_delayed(self.settings["global_cd"], self.reset_global_cd)

    @staticmethod
    def parse_playsound_arguments(message):
        """
        Available options:
        --volume VOLUME
        --cooldown COOLDOWN
        --enabled/--disabled
        """
        parser = ArgumentParser()
        parser.add_argument("--volume", dest="volume", type=int)
        # we parse this manually so we can allow "none" and things like that to unset the cooldown
        parser.add_argument("--cooldown", dest="cooldown", type=str)
        parser.add_argument("--enabled", dest="enabled", action="store_true")
        parser.add_argument("--disabled", dest="enabled", action="store_false")
        parser.set_defaults(volume=None, cooldown=None, enabled=None)

        try:
            args, unknown = parser.parse_known_args(message.split())
        except SystemExit:
            return False, False, False
        except:
            log.exception("Unhandled exception in add_command")
            return False, False, False

        # Strip options of any values that are set as None
        options = {k: v for k, v in vars(args).items() if v is not None}
        if len(unknown) < 1:
            # no name
            return False, False, False

        name = unknown[0]
        link = None if len(unknown) < 2 else " ".join(unknown[1:])

        return options, name, link

    @staticmethod
    def massage_name(name):
        if name is not None:
            return name.lower()

        return name

    re_valid_names = re.compile("^[a-z0-9\\-_]+$")

    @staticmethod
    def validate_name(name):
        return name is not None and PlaysoundModule.re_valid_names.match(name)

    re_valid_links = re.compile("^https://\\S*$")

    @staticmethod
    def validate_link(link):
        return link is not None and PlaysoundModule.re_valid_links.match(link)

    def update_link(self, bot, source, playsound, link):
        if link is not None:
            if not self.validate_link(link):
                bot.whisper(
                    source, "Error: Invalid link. Valid links must start with https:// " "and cannot contain spaces"
                )
                return False
            playsound.link = link
        return True

    @staticmethod
    def validate_volume(volume):
        return volume is not None and 0 <= volume <= 100

    def update_volume(self, bot, source, playsound, parsed_options):
        if "volume" in parsed_options:
            if not self.validate_volume(parsed_options["volume"]):
                bot.whisper(source, "Error: Volume must be between 0 and 100.")
                return False
            playsound.volume = parsed_options["volume"]
        return True

    @staticmethod
    def validate_cooldown(cooldown):
        return cooldown is None or cooldown >= 0

    def update_cooldown(self, bot, source, playsound, parsed_options):
        if "cooldown" in parsed_options:
            if parsed_options["cooldown"].lower() == "none":
                cooldown_int = None
            else:
                try:
                    cooldown_int = int(parsed_options["cooldown"])
                except ValueError:
                    bot.whisper(source, 'Error: Cooldown must be a number or the string "none".')
                    return False

            if not self.validate_cooldown(cooldown_int):
                bot.whisper(source, "Error: Cooldown must be positive.")
                return False

            playsound.cooldown = cooldown_int
        return True

    @staticmethod
    def update_enabled(bot, source, playsound, parsed_options):
        if "enabled" in parsed_options:
            playsound.enabled = parsed_options["enabled"]
        return True

    def add_playsound_command(self, bot, source, message, **rest):
        """Method for creating playsounds.
        Usage: !add playsound PLAYSOUNDNAME LINK [options]
        Multiple options available:
        --volume VOLUME
        --cooldown COOLDOWN
        --enabled/--disabled
        """

        options, name, link = self.parse_playsound_arguments(message)

        # the parser does not enforce a link being present because the edit function
        # doesn't require it strictly, so apart from "False" link is being checked
        # for being None here.
        if options is False or name is False or link is False or link is None:
            bot.whisper(
                source,
                "Invalid usage. Correct syntax: !add playsound <name> <link> "
                + "[--volume 0-100] [--cooldown 60/none] [--enabled/--disabled]",
            )
            return

        name = self.massage_name(name)

        if not self.validate_name(name):
            bot.whisper(
                source,
                "Invalid Playsound name. The playsound name may only contain lowercase latin letters, 0-9, -, or _. No spaces :rage:",
            )
            return

        with DBManager.create_session_scope() as session:
            count = session.query(Playsound).filter(Playsound.name == name).count()
            if count > 0:
                bot.whisper(
                    source,
                    "A Playsound with that name already exists. Use !edit playsound "
                    + "or !remove playsound to edit or delete it.",
                )
                return

            playsound = Playsound(name=name)

            if not self.update_link(bot, source, playsound, link):
                return

            if not self.update_volume(bot, source, playsound, options):
                return

            if not self.update_cooldown(bot, source, playsound, options):
                return

            if not self.update_enabled(bot, source, playsound, options):
                return

            session.add(playsound)
            bot.whisper(source, "Successfully added your playsound.")

    def edit_playsound_command(self, bot, source, message, **rest):
        """Method for editing playsounds.
        Usage: !edit playsound PLAYSOUNDNAME [LINK] [options]
        Multiple options available:
        --volume VOLUME
        --cooldown COOLDOWN
        --enabled/--disabled
        """

        options, name, link = self.parse_playsound_arguments(message)

        if options is False or name is False or link is False:
            bot.whisper(
                source,
                "Invalid usage. Correct syntax: !edit playsound <name> [link] "
                + "[--volume 0-100] [--cooldown 60/none] [--enabled/--disabled]",
            )
            return

        with DBManager.create_session_scope() as session:
            playsound = session.query(Playsound).filter(Playsound.name == name).one_or_none()
            if playsound is None:
                bot.whisper(
                    source,
                    "No playsound with that name exists. You can create playsounds with "
                    "!add playsound <name> <link> [options].",
                )
                return

            if not self.update_link(bot, source, playsound, link):
                return

            if not self.update_volume(bot, source, playsound, options):
                return

            if not self.update_cooldown(bot, source, playsound, options):
                return

            if not self.update_enabled(bot, source, playsound, options):
                return

            session.add(playsound)
            bot.whisper(source, "Successfully edited your playsound.")

    @staticmethod
    def remove_playsound_command(bot, source, message, **rest):
        """Method for removing playsounds.
        Usage: !edit playsound PLAYSOUNDNAME
        """
        playsound_name = PlaysoundModule.massage_name(message.split(" ")[0])
        # check for empty string
        if not playsound_name:
            bot.whisper(source, "Invalid usage. Correct syntax: !remove playsound <name>")
            return

        with DBManager.create_session_scope() as session:
            playsound = session.query(Playsound).filter(Playsound.name == playsound_name).one_or_none()

            if playsound is None:
                bot.whisper(source, "No playsound with that name exists.")
                return

            session.delete(playsound)
            bot.whisper(source, "Successfully deleted your playsound.")

    @staticmethod
    def debug_playsound_command(bot, source, message, **rest):
        """Method for debugging (printing info about) playsounds.
        Usage: !debug playsound PLAYSOUNDNAME
        """
        playsound_name = PlaysoundModule.massage_name(message.split(" ")[0])
        # check for empty string
        if not playsound_name:
            bot.whisper(source, "Invalid usage. Correct syntax: !debug playsound <name>")
            return

        with DBManager.create_session_scope() as session:
            playsound = session.query(Playsound).filter(Playsound.name == playsound_name).one_or_none()

            if playsound is None:
                bot.whisper(source, "No playsound with that name exists.")
                return

            bot.whisper(
                source,
                f"name={playsound.name}, link={playsound.link}, volume={playsound.volume}, cooldown={playsound.cooldown}, enabled={playsound.enabled}",
            )

    def load_commands(self, **options):
        from pajbot.models.command import Command
        from pajbot.models.command import CommandExample

        self.commands["#playsound"] = Command.raw_command(
            self.play_sound,
            tokens_cost=self.settings["token_cost"],
            cost=self.settings["point_cost"],
            sub_only=self.settings["sub_only"],
            delay_all=0,
            delay_user=0,
            description="Play a sound on stream!",
            can_execute_with_whisper=self.settings["can_whisper"],
            examples=[
                CommandExample(
                    None,
                    'Play the "doot" sample',
                    chat="user:!#playsound doot\n" "bot>user:Successfully played the sound doot on stream!",
                ).parse()
            ],
        )

        self.commands["#playsound"].long_description = 'Playsounds can be tried out <a href="/playsounds">here</a>'

        self.commands["add"] = Command.multiaction_command(
            level=100,
            delay_all=0,
            delay_user=0,
            default=None,
            command="add",
            commands={
                "playsound": Command.raw_command(
                    self.add_playsound_command,
                    level=500,
                    delay_all=0,
                    delay_user=0,
                    description="Creates a new playsound",
                    examples=[
                        CommandExample(
                            None,
                            "Create a new playsound",
                            chat="user:!add playsound doot https://i.nuuls.com/Bb4aX.mp3\n"
                            "bot>user:Successfully created your playsound",
                            description='Creates the "doot" playsound with the given link.',
                        ).parse(),
                        CommandExample(
                            None,
                            "Create a new playsound and sets volume",
                            chat="user:!add playsound doot https://i.nuuls.com/Bb4aX.mp3 --volume 50\n"
                            "bot>user:Successfully created your playsound",
                            description='Creates the "doot" playsound with the given link and 50% volume.',
                        ).parse(),
                        CommandExample(
                            None,
                            "Create a new playsound and sets cooldown",
                            chat="user:!add playsound doot https://i.nuuls.com/Bb4aX.mp3 --cooldown 60\n"
                            "bot>user:Successfully created your playsound",
                            description='Creates the "doot" playsound with the given link and 1 minute cooldown.',
                        ).parse(),
                        CommandExample(
                            None,
                            "Create a new playsound and disable it",
                            chat="user:!add playsound doot https://i.nuuls.com/Bb4aX.mp3 --disabled\n"
                            "bot>user:Successfully created your playsound",
                            description='Creates the "doot" playsound with the given link and initially disables it.',
                        ).parse(),
                    ],
                )
            },
        )

        self.commands["edit"] = Command.multiaction_command(
            level=100,
            delay_all=0,
            delay_user=0,
            default=None,
            command="edit",
            commands={
                "playsound": Command.raw_command(
                    self.edit_playsound_command,
                    level=500,
                    delay_all=0,
                    delay_user=0,
                    description="Edits an existing playsound",
                    examples=[
                        CommandExample(
                            None,
                            "Edit an existing playsound's link",
                            chat="user:!edit playsound doot https://i.nuuls.com/Bb4aX.mp3\n"
                            "bot>user:Successfully edited your playsound",
                            description='Updates the link of the "doot" playsound.',
                        ).parse(),
                        CommandExample(
                            None,
                            "Edit an existing playsound's volume",
                            chat="user:!edit playsound doot --volume 50\n"
                            "bot>user:Successfully edited your playsound",
                            description='Updates the volume of the "doot" playsound to 50%.',
                        ).parse(),
                        CommandExample(
                            None,
                            "Edit an existing playsound's cooldown",
                            chat="user:!edit playsound doot --cooldown 60\n"
                            "bot>user:Successfully edited your playsound",
                            description='Updates the cooldown of the "doot" playsound to 1 minute.',
                        ).parse(),
                        CommandExample(
                            None,
                            "Disable an existing playsound",
                            chat="user:!edit playsound doot --disabled\n" "bot>user:Successfully edited your playsound",
                            description='Disables the "doot" playsound.',
                        ).parse(),
                        CommandExample(
                            None,
                            "Enable an existing playsound",
                            chat="user:!edit playsound doot --enabled\n" "bot>user:Successfully edited your playsound",
                            description='Enables the "doot" playsound.',
                        ).parse(),
                    ],
                )
            },
        )

        self.commands["remove"] = Command.multiaction_command(
            level=100,
            delay_all=0,
            delay_user=0,
            default=None,
            command="remove",
            commands={
                "playsound": Command.raw_command(
                    self.remove_playsound_command,
                    level=500,
                    delay_all=0,
                    delay_user=0,
                    description="Removes an existing playsound",
                    examples=[
                        CommandExample(
                            None,
                            "Remove an existing playsound",
                            chat="user:!remove playsound doot\n" "bot>user:Successfully removed your playsound",
                            description='Removes the "doot" playsound.',
                        ).parse()
                    ],
                )
            },
        )

        self.commands["debug"] = Command.multiaction_command(
            level=100,
            delay_all=0,
            delay_user=0,
            default=None,
            command="debug",
            commands={
                "playsound": Command.raw_command(
                    self.debug_playsound_command,
                    level=250,
                    delay_all=0,
                    delay_user=0,
                    description="Prints data about a playsound",
                    examples=[
                        CommandExample(
                            None,
                            'Get information about the "doot" playsound',
                            chat="user:!debug playsound doot\n"
                            "bot>user: name=doot, link=https://i.nuuls.com/Bb4aX.mp3, volume=100, "
                            "cooldown=None, enabled=True",
                        ).parse()
                    ],
                )
            },
        )
