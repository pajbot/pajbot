from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import logging

from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.models.user import User, UserBasics
from pajbot.modules import BaseModule, ModuleSetting
from pajbot.modules.chat_alerts import ChatAlertModule

if TYPE_CHECKING:
    from pajbot.bot import Bot

log = logging.getLogger(__name__)


class SubAlertModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Subscription Alert"
    DESCRIPTION = "Prints a message in chat/whispers when a user re/subscribes"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = True
    PARENT_MODULE = ChatAlertModule
    SETTINGS = [
        ModuleSetting(
            key="chat_message",
            label="Enable a chat message for someone who subscribed",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="new_sub",
            label="New sub chat message | Available arguments: {username}",
            type="text",
            required=True,
            placeholder="Sub hype! {username} just subscribed PogChamp",
            default="Sub hype! {username} just subscribed PogChamp",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="new_prime_sub",
            label="New prime sub chat message | Available arguments: {username}",
            type="text",
            required=True,
            placeholder="Thank you for smashing that prime button! {username} PogChamp",
            default="Thank you for smashing that prime button! {username} PogChamp",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="new_gift_sub",
            label="New gift sub chat message | Available arguments: {username}, {gifted_by}",
            type="text",
            required=True,
            placeholder="{gifted_by} gifted a fresh sub to {username}! PogChamp",
            default="{gifted_by} gifted a fresh sub to {username}! PogChamp",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="resub",
            label="Resub chat message | Available arguments: {username}, {num_months}, {substreak_string}",
            type="text",
            required=True,
            placeholder="Resub hype! {username} just subscribed, {num_months} months in a row PogChamp <3",
            default="Resub hype! {username} just subscribed, {num_months} months in a row PogChamp <3",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="resub_prime",
            label="Resub chat message (Prime sub) | Available arguments: {username}, {num_months}, {substreak_string}",
            type="text",
            required=True,
            placeholder="Thank you for smashing it {num_months} in a row {username}",
            default="Thank you for smashing it {num_months} in a row {username}",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="resub_gift",
            label="Resub chat message (Gift sub) | Available arguments: {username}, {num_months}, {gifted_by}, {substreak_string}",
            type="text",
            required=True,
            placeholder="{username} got gifted a resub by {gifted_by}, that's {num_months} months in a row PogChamp",
            default="{username} got gifted a resub by {gifted_by}, that's {num_months} months in a row PogChamp",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="gift_upgrade",
            label="Updgraded gift sub chat message. Leave empty to disable | Available arguments: {username}",
            type="text",
            required=True,
            placeholder="Thank you for upgrading your gift sub {username}! PogChamp <3",
            default="Thank you for upgrading your gift sub {username}! PogChamp <3",
            constraints={"max_str_len": 400},
        ),
        ModuleSetting(
            key="extend_sub",
            label="Chat message for users that extend their sub (subtember-related). Leave empty to disable | Available arguments: {username}",
            type="text",
            required=True,
            placeholder="Thank you for extending your sub {username}! PogChamp",
            default="Thank you for extending your sub {username}! PogChamp",
            constraints={"max_str_len": 400},
        ),
        ModuleSetting(
            key="substreak_string",
            label="Sub streak string. Empty if streak was not shared | Available arguments: {username}, {num_months}",
            type="text",
            required=True,
            placeholder="{num_months} in a row PogChamp",
            default="{num_months} in a row PogChamp",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="whisper_message",
            label="Enable a whisper message for someone who subscribed",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="whisper_after",
            label="Whisper the message after X seconds",
            type="number",
            required=True,
            placeholder="",
            default=5,
            constraints={"min_value": 1, "max_value": 120},
        ),
        ModuleSetting(
            key="new_sub_whisper",
            label="Whisper message for new subs | Available arguments: {username}",
            type="text",
            required=True,
            placeholder="Thank you for subscribing {username} <3",
            default="Thank you for subscribing {username} <3",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="resub_whisper",
            label="Whisper message for resubs | Available arguments: {username}, {num_months}",
            type="text",
            required=True,
            placeholder="Thank you for subscribing for {num_months} months in a row {username} <3",
            default="Thank you for subscribing for {num_months} months in a row {username} <3",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="gift_upgrade_whisper",
            label="Whisper message for upgraded gift subs. Leave empty to disable | Available arguments: {username}",
            type="text",
            required=True,
            placeholder="Thank you for upgrading your gift sub {username}! PogChamp <3",
            default="",
        ),
        ModuleSetting(
            key="extend_sub_whisper",
            label="Whisper message for users that extend their sub (subtember-related). Leave empty to disable | Available arguments: {username}",
            type="text",
            required=True,
            placeholder="Thank you for extending your sub {username}! PogChamp",
            default="",
            constraints={"max_str_len": 400},
        ),
        ModuleSetting(
            key="grant_points_on_sub",
            label="Give points to user when they subscribe/resubscribe. 0 = off",
            type="number",
            required=True,
            placeholder="",
            default=0,
            constraints={"min_value": 0, "max_value": 1000000},
        ),
        ModuleSetting(
            key="alert_message_points_given",
            label="Message to announce points were given to user, leave empty to disable message. | Available arguments: {user}, {points}",
            type="text",
            required=True,
            default="{user} was given {points} points for subscribing! FeelsAmazingMan",
            constraints={"min_str_len": 0, "max_str_len": 300},
        ),
    ]

    def __init__(self, bot: Optional[Bot]) -> None:
        super().__init__(bot)

    def on_sub_shared(self, user: User) -> None:
        assert self.bot is not None

        if self.settings["grant_points_on_sub"] <= 0:
            return

        user.points += self.settings["grant_points_on_sub"]

        alert_message = self.settings["alert_message_points_given"]
        if alert_message != "":
            self.bot.say(alert_message.format(user=user, points=self.settings["grant_points_on_sub"]))

    def on_new_sub(self, user: User, sub_type: str, gifted_by: Optional[str] = None) -> None:
        """
        A new user just subscribed.
        Send the event to the websocket manager, and send a customized message in chat.
        Also increase the number of active subscribers in the database by one.
        """

        assert self.bot is not None

        self.on_sub_shared(user)

        self.bot.kvi["active_subs"].inc()

        payload = {"username": user.name, "gifted_by": gifted_by}
        self.bot.websocket_manager.emit("new_sub", payload)

        if self.settings["chat_message"] is True:
            if sub_type == "Prime":
                self.bot.say(self.get_phrase("new_prime_sub", **payload))
            else:
                if gifted_by:
                    self.bot.say(self.get_phrase("new_gift_sub", **payload))
                else:
                    self.bot.say(self.get_phrase("new_sub", **payload))

        if self.settings["whisper_message"] is True:
            self.bot.execute_delayed(
                self.settings["whisper_after"], self.bot.whisper, user, self.get_phrase("new_sub_whisper", **payload)
            )

    def on_resub(
        self, user: User, num_months: int, sub_type: str, gifted_by: Optional[str] = None, substreak_count: int = 0
    ) -> None:
        """
        A user just re-subscribed.
        Send the event to the websocket manager, and send a customized message in chat.
        """

        assert self.bot is not None

        self.on_sub_shared(user)

        payload = {"username": user.name, "num_months": num_months, "gifted_by": gifted_by}
        if substreak_count and substreak_count > 0:
            payload["substreak_string"] = self.get_phrase(
                "substreak_string", username=user.name, num_months=substreak_count, gifted_by=gifted_by
            )
        else:
            payload["substreak_string"] = ""
        self.bot.websocket_manager.emit("resub", payload)

        if self.settings["chat_message"] is True:
            if sub_type == "Prime":
                self.bot.say(self.get_phrase("resub_prime", **payload))
            else:
                if gifted_by:
                    self.bot.say(self.get_phrase("resub_gift", **payload))
                else:
                    self.bot.say(self.get_phrase("resub", **payload))

        if self.settings["whisper_message"] is True:
            self.bot.execute_delayed(
                self.settings["whisper_after"], self.bot.whisper, user, self.get_phrase("resub_whisper", **payload)
            )

    def on_gift_upgrade(self, user: User) -> None:
        assert self.bot is not None

        if self.settings["gift_upgrade"] != "":
            self.bot.say(self.settings["gift_upgrade"].format(user=user))

        if self.settings["gift_upgrade_whisper"] != "":
            self.bot.execute_delayed(
                self.settings["whisper_after"],
                self.bot.whisper,
                user,
                self.settings["gift_upgrade_whisper"].format(user=user),
            )

    def on_extend_sub(self, user: User) -> None:
        assert self.bot is not None

        if self.settings["extend_sub"] != "":
            self.bot.say(self.settings["extend_sub"].format(user=user))

        if self.settings["extend_sub_whisper"] != "":
            self.bot.execute_delayed(
                self.settings["whisper_after"],
                self.bot.whisper,
                user,
                self.settings["extend_sub_whisper"].format(user=user),
            )

    def on_usernotice(self, source: User, message: str, tags: dict[str, str]) -> bool:
        if "msg-id" not in tags:
            return True

        if tags["msg-id"] == "resub":
            num_months = -1
            substreak_count = 0
            if "msg-param-months" in tags:
                num_months = int(tags["msg-param-months"])
            if "msg-param-cumulative-months" in tags:
                num_months = int(tags["msg-param-cumulative-months"])
            if "msg-param-streak-months" in tags:
                substreak_count = int(tags["msg-param-streak-months"])
            if "msg-param-should-share-streak" in tags:
                should_share = bool(tags["msg-param-should-share-streak"])
                if not should_share:
                    substreak_count = 0

            if "msg-param-sub-plan" not in tags:
                log.debug(f"subalert msg-id is resub, but missing msg-param-sub-plan: {tags}")
                return True

            # log.debug('msg-id resub tags: {}'.format(tags))

            # TODO: Should we check room id with streamer ID here? Maybe that's for pajbot2 instead
            self.on_resub(source, num_months, tags["msg-param-sub-plan"], None, substreak_count)
            HandlerManager.trigger("on_user_resub", user=source, num_months=num_months)
        elif tags["msg-id"] == "subgift":
            num_months = 0
            substreak_count = 0
            if "msg-param-months" in tags:
                num_months = int(tags["msg-param-months"])
            if "msg-param-cumulative-months" in tags:
                num_months = int(tags["msg-param-cumulative-months"])
            if "msg-param-streak-months" in tags:
                substreak_count = int(tags["msg-param-streak-months"])
            if "msg-param-should-share-streak" in tags:
                should_share = bool(tags["msg-param-should-share-streak"])
                if not should_share:
                    substreak_count = 0

            if "display-name" not in tags:
                log.debug(f"subalert msg-id is subgift, but missing display-name: {tags}")
                return True

            with DBManager.create_session_scope() as db_session:
                receiver_id = tags["msg-param-recipient-id"]
                receiver_login = tags["msg-param-recipient-user-name"]
                receiver_name = tags["msg-param-recipient-display-name"]
                receiver = User.from_basics(db_session, UserBasics(receiver_id, receiver_login, receiver_name))

                if num_months > 1:
                    # Resub
                    self.on_resub(
                        receiver, num_months, tags["msg-param-sub-plan"], tags["display-name"], substreak_count
                    )
                    HandlerManager.trigger("on_user_resub", user=receiver, num_months=num_months)
                else:
                    # New sub
                    self.on_new_sub(receiver, tags["msg-param-sub-plan"], tags["display-name"])
                    HandlerManager.trigger("on_user_sub", user=receiver)
        elif tags["msg-id"] == "sub":
            if "msg-param-sub-plan" not in tags:
                log.debug(f"subalert msg-id is sub, but missing msg-param-sub-plan: {tags}")
                return True

            self.on_new_sub(source, tags["msg-param-sub-plan"])
            HandlerManager.trigger("on_user_sub", user=source)
        elif tags["msg-id"] == "giftpaidupgrade":
            self.on_gift_upgrade(source)
        elif tags["msg-id"] == "extendsub":
            self.on_extend_sub(source)
        else:
            log.debug(f"Unhandled msg-id: {tags['msg-id']} - tags: {tags}")

        return True

    def enable(self, bot: Optional[Bot]) -> None:
        if bot is not None:
            HandlerManager.add_handler("on_usernotice", self.on_usernotice)

    def disable(self, bot: Optional[Bot]) -> None:
        if bot is not None:
            HandlerManager.remove_handler("on_usernotice", self.on_usernotice)
