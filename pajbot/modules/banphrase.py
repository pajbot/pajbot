from typing import Any, List

import logging

from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.models.command import Command, CommandExample
from pajbot.modules.base import BaseModule

log = logging.getLogger(__name__)


class BanphraseModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Banphrases"
    DESCRIPTION = "Looks at each message for banned phrases, and takes actions accordingly"
    ENABLED_DEFAULT = True
    CATEGORY = "Moderation"
    SETTINGS: List[Any] = []

    def is_message_bad(self, source, msg_raw, _event):
        res = self.bot.banphrase_manager.check_message(msg_raw, source)
        if res is not False:
            self.bot.banphrase_manager.punish(source, res)
            return True

        return False  # message was ok

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message, priority=150, run_if_propagation_stopped=True)

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)

    def on_message(self, source, message, whisper, event, **rest):
        if whisper:
            return
        if source.level >= 500 or source.moderator:
            return

        if self.is_message_bad(source, message, event):
            # we matched a filter.
            # return False so no more code is run for this message
            return False

    @staticmethod
    def add_banphrase(bot, source, message, **rest):
        """Method for creating and editing banphrases.
        Usage: !add banphrase BANPHRASE [options]
        Multiple options available:
        --length LENGTH
        --perma/--no-perma
        --notify/--no-notify
        """

        if message:
            options, phrase = bot.banphrase_manager.parse_banphrase_arguments(message)

            if options is False:
                bot.whisper(source, "Invalid banphrase")
                return False

            options["added_by"] = source.id
            options["edited_by"] = source.id

            banphrase, new_banphrase = bot.banphrase_manager.create_banphrase(phrase, **options)

            if new_banphrase is True:
                bot.whisper(source, f"Added your banphrase (ID: {banphrase.id})")
                AdminLogManager.post("Banphrase added", source, banphrase.id, banphrase.phrase)
                return True

            banphrase.set(**options)
            banphrase.data.set(edited_by=options["edited_by"])
            DBManager.session_add_expunge(banphrase)
            bot.banphrase_manager.commit()
            bot.whisper(
                source,
                f"Updated your banphrase (ID: {banphrase.id}) with ({', '.join([key for key in options if key != 'added_by'])})",
            )
            AdminLogManager.post("Banphrase edited", source, banphrase.id, banphrase.phrase)

    @staticmethod
    def remove_banphrase(bot, source, message, **rest):
        if not message:
            bot.whisper(source, "Usage: !remove banphrase (BANPHRASE_ID)")
            return False

        banphrase_id = None
        try:
            banphrase_id = int(message)
        except ValueError:
            pass

        banphrase = bot.banphrase_manager.find_match(message=message, banphrase_id=banphrase_id)

        if banphrase is None:
            bot.whisper(source, "No banphrase with the given parameters found")
            return False

        AdminLogManager.post("Banphrase removed", source, banphrase.id, banphrase.phrase)
        bot.whisper(source, f"Successfully removed banphrase with id {banphrase.id}")
        bot.banphrase_manager.remove_banphrase(banphrase)

    def load_commands(self, **options):
        self.commands["add"] = Command.multiaction_command(
            level=100,
            delay_all=0,
            delay_user=0,
            default=None,
            command="add",
            commands={
                "banphrase": Command.raw_command(
                    self.add_banphrase,
                    level=500,
                    description="Add a banphrase!",
                    delay_all=0,
                    delay_user=0,
                    examples=[
                        CommandExample(
                            None,
                            "Create a banphrase",
                            chat="user:!add banphrase testman123\n" "bot>user:Inserted your banphrase (ID: 83)",
                            description="This creates a banphrase with the default settings. Whenever a non-moderator types testman123 in chat they will be timed out for 300 seconds and notified through a whisper that they said something they shouldn't have said",
                        ).parse(),
                        CommandExample(
                            None,
                            "Create a banphrase that permabans people",
                            chat="user:!add banphrase testman123 --perma\n" "bot>user:Inserted your banphrase (ID: 83)",
                            description="This creates a banphrase that permabans the user who types testman123 in chat. The user will be notified through a whisper that they said something they shouldn't have said",
                        ).parse(),
                        CommandExample(
                            None,
                            "Create a banphrase that permabans people without a notification",
                            chat="user:!add banphrase testman123 --perma --no-notify\n"
                            "bot>user:Inserted your banphrase (ID: 83)",
                            description="This creates a banphrase that permabans the user who types testman123 in chat",
                        ).parse(),
                        CommandExample(
                            None,
                            "Change the default timeout length for a banphrase",
                            chat="user:!add banphrase testman123 --time 123\n"
                            "bot>user:Updated the given banphrase (ID: 83) with (time, extra_args)",
                            description="Changes the default timeout length to a custom time of 123 seconds",
                        ).parse(),
                        CommandExample(
                            None,
                            "Make it so a banphrase cannot be triggered by subs",
                            chat="user:!add banphrase testman123 --subimmunity\n"
                            "bot>user:Updated the given banphrase (ID: 83) with (sub_immunity)",
                            description="Changes a command so that the banphrase can only be triggered by people who are not subscribed to the channel.",
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
                "banphrase": Command.raw_command(
                    self.remove_banphrase,
                    level=500,
                    delay_all=0,
                    delay_user=0,
                    description="Remove a banphrase!",
                    examples=[
                        CommandExample(
                            None,
                            "Remove a banphrase",
                            chat="user:!remove banphrase KeepoKeepo\n"
                            "bot>user:Successfully removed banphrase with id 33",
                            description="Removes a banphrase with the trigger KeepoKeepo.",
                        ).parse(),
                        CommandExample(
                            None,
                            "Remove a banphrase with the given ID.",
                            chat="user:!remove banphrase 25\n" "bot>user:Successfully removed banphrase with id 25",
                            description="Removes a banphrase with id 25",
                        ).parse(),
                    ],
                )
            },
        )
