from typing import TYPE_CHECKING, Any, Optional

import logging

from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager, HandlerResponse, ResponseMeta
from pajbot.message_event import MessageEvent
from pajbot.response import BanResponse, TimeoutResponse
from pajbot.models.command import Command, CommandExample
from pajbot.models.emote import EmoteInstance, EmoteInstanceCountMap
from pajbot.models.user import User
from pajbot.modules.base import BaseModule
from pajbot.modules.warning import WarningModule

if TYPE_CHECKING:
    from pajbot.bot import Bot

log = logging.getLogger(__name__)


class BanphraseModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Banphrases"
    DESCRIPTION = "Looks at each message for banned phrases, and takes actions accordingly"
    ENABLED_DEFAULT = True
    CATEGORY = "Moderation"
    SETTINGS: list[Any] = []

    def is_message_bad(self, source, msg_raw, _event) -> bool:
        if self.bot is None:
            return False

        res = self.bot.banphrase_manager.check_message(msg_raw, source)
        if res is not False:
            self.bot.banphrase_manager.punish(source, res)
            return True

        return False  # message was ok

    def check_message(self, source: User, msg_raw: str) -> TimeoutResponse | BanResponse | None:
        if self.bot is None:
            return None

        res = self.bot.banphrase_manager.check_message(msg_raw, source)
        if res is not False:
            reason = f"Banned phrase {res.id} ({res.name})"
            if res.permanent:
                return BanResponse(source.id, reason=reason)

            warning_module = self.bot.module_manager["warning"]
            if warning_module is not None:
                assert isinstance(warning_module, WarningModule)

            timeout_length, _punishment = source.timeout(
                res.length, warning_module=warning_module, use_warnings=res.warning
            )
            return TimeoutResponse(source.id, timeout_length, reason=reason)

        return None

    def enable(self, bot) -> None:
        if bot:
            HandlerManager.register_on_message(self.on_message, priority=150)

    def disable(self, bot) -> None:
        if bot:
            HandlerManager.unregister_on_message(self.on_message)

    async def on_message(
        self,
        source: User,
        message: str,
        emote_instances: list[EmoteInstance],
        emote_counts: EmoteInstanceCountMap,
        is_whisper: bool,
        urls: list[str],
        msg_id: str | None,
        event: MessageEvent,
        meta: ResponseMeta,
    ) -> HandlerResponse:
        if is_whisper:
            meta.add(__name__, "message was whisper")
            return HandlerResponse.null()
        if source.level >= 500:
            meta.add(__name__, "chatter level >= 500")
            return HandlerResponse.null()
        if source.moderator:
            meta.add(__name__, "chatter was mod")
            return HandlerResponse.null()

        action = self.check_message(source, message)
        if action is None:
            log.info("on_message2: Message did not hit a banphrase(?), do nothing")
            return HandlerResponse.null()

        log.info(f"on_message2: {message} message hit a banphrase!!!!!!!")
        # we matched a filter.
        # return False so no more code is run for this message
        res = HandlerResponse()
        res.stop = True
        res.actions.append(action)
        return res

    @staticmethod
    def add_banphrase(bot, source, message, **rest):
        """Method for creating and editing banphrases.
        Usage: !add banphrase BANPHRASE [options]
        Multiple options available:
        --length LENGTH
        --perma/--no-perma
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
                            chat="user:!add banphrase testman123\nbot>user:Inserted your banphrase (ID: 83)",
                            description="This creates a banphrase with the default settings. Whenever a non-moderator types testman123 in chat they will be timed out for 300 seconds and notified through a whisper that they said something they shouldn't have said",
                        ).parse(),
                        CommandExample(
                            None,
                            "Create a banphrase that permabans people",
                            chat="user:!add banphrase testman123 --perma\nbot>user:Inserted your banphrase (ID: 83)",
                            description="This creates a banphrase that permabans the user who types testman123 in chat. The user will be notified through a whisper that they said something they shouldn't have said",
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
                            chat="user:!remove banphrase 25\nbot>user:Successfully removed banphrase with id 25",
                            description="Removes a banphrase with id 25",
                        ).parse(),
                    ],
                )
            },
        )
