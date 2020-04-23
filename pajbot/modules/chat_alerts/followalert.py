import logging

from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.models.user import User, UserBasics
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting
from pajbot.modules.chat_alerts import ChatAlertModule

log = logging.getLogger(__name__)


class FollowAlertModule(BaseModule):
    ID = __name__.split(".")[-1]
    NAME = "Follow Alert"
    DESCRIPTION = "Prints a message in chat/whispers when a user follows the channel"
    CATEGORY = "Feature"
    ENABLED_DEFAULT = True
    PARENT_MODULE = ChatAlertModule
    SETTINGS = [
        ModuleSetting(
            key="chat_message",
            label="Enable a chat message for someone who follows",
            type="boolean",
            required=True,
            default=True,
        ),
        ModuleSetting(
            key="new_follow",
            label="New follow chat message | Available arguments: {username}",
            type="text",
            required=True,
            placeholder="Thanks for following {username}! PogChamp",
            default="Thanks for following {username}! PogChamp",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="whisper_message",
            label="Enable a whisper message for someone who follows",
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
            key="new_follow_whisper",
            label="Whisper message for new followers | Available arguments: {username}",
            type="text",
            required=True,
            placeholder="Thank you for following {username} <3",
            default="Thank you for following {username} <3",
            constraints={"min_str_len": 10, "max_str_len": 400},
        ),
        ModuleSetting(
            key="grant_points_on_follow",
            label="Give points to user when they follow. 0 = off",
            type="number",
            required=True,
            placeholder="",
            default=0,
            constraints={"min_value": 0, "max_value": 50000},
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)

    def on_sub_shared(self, user):
        if self.settings["grant_points_on_follow"] <= 0:
            return

        user.points += self.settings["grant_points_on_follow"]
        self.bot.say(f"{user} was given {self.settings['grant_points_on_follow']} points for following! FeelsAmazingMan")

    def on_new_sub(self, user, sub_type, gifted_by=None):
        """
        A new user just subscribed.
        Send the event to the websocket manager, and send a customized message in chat.
        Also increase the number of active subscribers in the database by one.
        """

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

    def on_resub(self, user, num_months, sub_type, gifted_by=None, substreak_count=0):
        """
        A user just re-subscribed.
        Send the event to the websocket manager, and send a customized message in chat.
        """

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

    def on_usernotice(self, source, tags, **rest):
        if "msg-id" not in tags:
            return

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
                return

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
                return

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
                return

            self.on_new_sub(source, tags["msg-param-sub-plan"])
            HandlerManager.trigger("on_user_sub", user=source)
        else:
            log.debug(f"Unhandled msg-id: {tags['msg-id']} - tags: {tags}")

    def enable(self, bot):
        HandlerManager.add_handler("on_usernotice", self.on_usernotice)

    def disable(self, bot):
        HandlerManager.remove_handler("on_usernotice", self.on_usernotice)
