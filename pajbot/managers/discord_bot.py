import logging
from pajbot.managers.db import DBManager
from pajbot import utils
from pajbot.models.user_connection import UserConnections
from pajbot.models.user import User
import discord
import asyncio
import json
import threading
from datetime import datetime, timedelta

log = logging.getLogger("pajbot")


class Command(object):
    def __init__(self, name, handler, admin=False, args=""):  # --arg-req(name) --arg-opt(age)
        self.name = name
        self.admin = admin

        self.args = []

        if not asyncio.iscoroutinefunction(handler):
            handler = asyncio.coroutine(handler)
        self.handler = handler
        self.help = handler.__doc__ or ""

    def __str__(self):
        return "<Command {}: admin={}, args={}>".format(self.name, self.admin, len(self.args) > 0)

    async def call(self, message):
        await self.handler(message)


class CustomClient(discord.Client):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    async def on_ready(self):
        self.bot.guild = self.get_guild(int(self.bot.settings["discord_guild"]))
        if not self.bot.guild:
            log.error("Discord Guild not found!")
            return
        log.info(f"Discord Bot has started!")
        await self.bot.check_discord_roles()

    async def on_message(self, message):
        if not message.content.startswith("!"):
            return
        data = message.content.split("!")
        if len(data) <= 1:
            return
        cmd = self.bot.commands.get(data[1].split(" ")[0])
        if not cmd:
            return
        try:
            await cmd.call(message)
        except Exception as e:
            log.error(e)


class DiscordBotManager(object):
    def __init__(self, bot, redis):
        self.bot = bot
        self.client = CustomClient(self)
        self.commands = {}
        self.add_command("connections", self._connections)
        self.add_command("check", self._check)
        self.add_command("bytier", self._get_users_by_tier)
        self.add_command("count", self._count_by_tier)

        self.private_loop = asyncio.get_event_loop()
        self.redis = redis

        self.guild = None
        self.settings = None
        self.thread = None
        self.discord_task = self.schedule_task_periodically(300, self.check_discord_roles)

        queued_subs = self.redis.get("queued-subs-discord")
        unlinkinfo = self.redis.get("unlinks-subs-discord")
        if unlinkinfo is None or "array" in json.loads(unlinkinfo):
            data = {}
            self.redis.set("unlinks-subs-discord", json.dumps(data))
        if queued_subs is None or "array" in json.loads(queued_subs):
            data = {}
            self.redis.set("queued-subs-discord", json.dumps(data))

    def add_command(self, *args, **kwargs):
        cmd = Command(*args, **kwargs)
        self.commands[cmd.name] = cmd

    async def _check(self, message):
        if not self.guild:
            return

        admin_role = self.guild.get_role(int(self.settings["admin_role"]))

        requestor = self.guild.get_member(message.author.id)
        if not requestor:
            return

        if admin_role in requestor.roles:
            await self.check_discord_roles()
            await self.private_message(requestor, f"Check complete!")
            return

    async def _count_by_tier(self, message):
        if not self.guild:
            return

        requestor = self.guild.get_member(message.author.id)
        if not requestor:
            return

        with DBManager.create_session_scope() as db_session:
            admin_role = self.guild.get_role(int(self.settings["admin_role"]))
            if admin_role in requestor.roles:
                args = message.content.split(" ")[1:]
                if len(args) > 0:
                    requested_tier = args[0]
                    try:
                        requested_tier = int(requested_tier)
                    except:
                        return
                    count = UserConnections._count_by_tier(db_session, requested_tier)
                    if requested_tier == 0:
                        count += UserConnections._count_by_tier(db_session, None)
                else:
                    count = UserConnections._count(db_session)
                await self.private_message(
                    requestor,
                    f"There are {count} tier {requested_tier} subs" if len(args) > 0 else f"There are {count} users connected"
                )   

    async def _get_users_by_tier(self, message):
        if not self.guild:
            return

        requestor = self.guild.get_member(message.author.id)
        if not requestor:
            return

        with DBManager.create_session_scope() as db_session:
            admin_role = self.guild.get_role(int(self.settings["admin_role"]))
            if admin_role in requestor.roles:
                args = message.content.split(" ")[1:]
                page = 1
                if len(args) > 0:
                    requested_tier = args[0]
                    try:
                        requested_tier = int(requested_tier)
                    except:
                        return

                    return_message = ""
                    all_users_con = UserConnections._by_tier(db_session, requested_tier)
                    if requested_tier == 0:
                        all_users_con = all_users_con + UserConnections._by_tier(db_session, None)
                    for user_con in all_users_con:
                        user = user_con.twitch_user
                        if (not user.tier and requested_tier != 0) or (user.tier and user.tier != requested_tier):
                            continue

                        discord = await self.get_discord_string(user_con.discord_user_id)
                        temp_message = f"\nTwitch: {user} (<https://twitch.tv/{user.login}>){discord}\nSteam: <https://steamcommunity.com/profiles/{user_con.steam_id}>\n"

                        if len(return_message) + len(temp_message) > 1300:
                            await self.private_message(
                                requestor, f"All tier {requested_tier} subs (Page {page}):\n" + return_message
                            )
                            page += 1
                            return_message = ""

                        return_message += temp_message

                    await self.private_message(
                        requestor,
                        f"All tier {requested_tier} subs (Page {page}):\n"
                        + return_message
                        + ("There are none!" if return_message == "" else ""),
                    )

    async def get_discord_string(self, id):
        if not self.guild:
            return
        id = int(id)
        member = self.guild.get_member(id) or await self.get_user_api(id)
        return (
            f"\nDiscord: {member.display_name}#{member.discriminator} (<https://discordapp.com/users/{member.id}>)"
            if member
            else ""
        )

    async def get_user_api(self, id):
        try:
            return await self.client.fetch_user(id)
        except (discord.NotFound, discord.HTTPException) as e:
            log.warning(e)
            return None

    async def _connections(self, message):
        if not self.guild:
            return

        requestor = self.guild.get_member(message.author.id)
        if not requestor:
            return

        with DBManager.create_session_scope() as db_session:
            userconnections = None
            admin_role = self.guild.get_role(int(self.settings["admin_role"]))
            if admin_role in requestor.roles:
                args = message.content.split(" ")[1:]
                if len(args) > 0:
                    check_user = args[0]
                    user = User.find_by_user_input(db_session, check_user)
                    if user:
                        userconnections = db_session.query(UserConnections).filter_by(twitch_id=user.id).one_or_none()
                    if not userconnections:
                        await self.private_message(requestor, f"Connection data not found for user " + args[0])
                        return
            if not userconnections:
                userconnections = (
                    db_session.query(UserConnections).filter_by(discord_user_id=str(requestor.id)).one_or_none()
                )
            if not userconnections:
                await self.private_message(
                    requestor,
                    f"You have not set up your account info yet, go to https://{self.bot.bot_domain}/connections to pair your twitch and steam to your discord account!",
                )
                return
            user = userconnections.twitch_user
            if user.tier is None:
                tier = 0
            elif user.tier >= 1:
                tier = user.tier
            else:
                tier = 0
            discord = await self.get_discord_string(userconnections.discord_user_id)
            await self.private_message(
                message.author,
                f"Tier {tier} sub:\nTwitch: {user} (<https://twitch.tv/{user.login}>){discord}\nSteam: <https://steamcommunity.com/profiles/{userconnections.steam_id}>",
            )

    async def private_message(self, member, message):
        message = discord.utils.escape_markdown(message)
        await self._private_message(member, message)

    async def remove_role(self, member, role):
        await self._remove_role(member, role)

    async def add_role(self, member, role):
        await self._add_role(member, role)

    async def _private_message(self, member, message):
        await member.create_dm()
        await member.dm_channel.send(message)

    async def _remove_role(self, member, role):
        await member.remove_roles(role)

    async def _add_role(self, member, role):
        await member.add_roles(role)

    async def check_discord_roles(self):
        if not self.guild:
            return

        tier2_role = self.guild.get_role(int(self.settings["tier2_role"]))
        tier3_role = self.guild.get_role(int(self.settings["tier3_role"]))
        notify_role = self.guild.get_role(int(self.settings["notify_role"]))
        ignore_role = self.guild.get_role(int(self.settings["ignore_role"]))

        roles_allocated = {
            "tier2_role": tier2_role,
            "tier3_role": tier3_role,
            "notify_role": notify_role,
            "ignore_role": ignore_role,
        }

        quick_dict_twitch = {}
        quick_dict_discord = {}
        subs_to_return = {}

        queued_subs = json.loads(self.redis.get("queued-subs-discord"))
        unlinkinfo = json.loads(self.redis.get("unlinks-subs-discord"))

        messages_add = []
        messages_remove = []
        messages_other = []

        with DBManager.create_session_scope() as db_session:
            for twitch_id in unlinkinfo:
                unlinks = unlinkinfo[twitch_id]
                member = self.guild.get_member(int(unlinks["discord_user_id"]))
                if member:
                    if tier3_role is not None and tier3_role in member.roles:
                        await self.remove_role(member, tier3_role)
                    if tier2_role is not None and tier2_role in member.roles:
                        await self.remove_role(member, tier2_role)
                user = User.find_by_id(db_session, twitch_id)
                steam_id = unlinks["steam_id"]
                tier = unlinks["discord_tier"]
                if self.settings["notify_on_unsub"] and tier > 1 and self.settings[f"notify_on_tier{tier}"]:
                    discord = await self.get_discord_string(unlinks["discord_user_id"])
                    messages_other.append(
                        f"\n\nAccount Data Unlinked: Tier {tier} sub removal notification:\nTwitch: {user} (<https://twitch.tv/{user.login}>){discord}\nSteam: <https://steamcommunity.com/profiles/{steam_id}>"
                    )

            self.redis.set("unlinks-subs-discord", json.dumps({}))

            all_connections = db_session.query(UserConnections).all()

            for connection in all_connections:
                user = connection.twitch_user
                member = self.guild.get_member(int(connection.discord_user_id))
                discord = await self.get_discord_string(connection.discord_user_id)
                steam_id = connection.steam_id

                if (
                    not user or discord == ""
                ):  # Discord doesnt exist or Somehow the twitch doesnt exist in our database so we prune
                    connection._remove(db_session)
                    continue

                quick_dict_twitch[connection.twitch_id] = connection
                quick_dict_discord[connection.discord_user_id] = connection

                if not connection.twitch_login:
                    connection._update_twitch_login(db_session, user.login)
                if connection.twitch_login != user.login:
                    if connection.tier > 1:
                        if self.settings["notify_on_name_change"] and self.settings[f"notify_on_tier{connection.tier}"]:
                            messages_other.append(
                                f"\n\nTwitch login changed for a tier {connection.tier} sub\nSteam: <https://steamcommunity.com/profiles/{connection.steam_id}>\nOld Twitch: {connection.twitch_login}\nNew Twitch: {user.login}"
                            )
                    connection._update_twitch_login(db_session, user.login)

                if member and member.display_name + "#" + member.discriminator != connection.discord_username:
                    connection._update_discord_username(db_session, member.display_name + "#" + member.discriminator)

                db_session.commit()

                if not ignore_role or member and ignore_role not in member.roles:
                    role = roles_allocated[f"tier{user.tier}_role"] if user.tier and user.tier > 1 else None
                    if user.tier == connection.tier:
                        if role and role not in member.roles:
                            await self.add_role(member, role)
                    else:
                        if user.tier and user.tier > 1:
                            if (
                                self.settings["notify_on_unsub"]
                                and connection.tier > 1
                                and self.settings[f"notify_on_tier{connection.tier}"]
                            ):
                                messages_remove.append(
                                    f"\n\nTier {connection.tier} sub removal notification:\nTwitch: {user} (<https://twitch.tv/{user.login}>){discord}\nSteam: <https://steamcommunity.com/profiles/{steam_id}>"
                                )
                            connection._update_tier(db_session, user.tier)
                        if role:
                            if (
                                self.settings["notify_on_new_sub"]
                                and user.tier > 1
                                and self.settings[f"notify_on_tier{user.tier}"]
                            ):
                                messages_add.append(
                                    f"\n\nTier {user.tier} sub notification:\nTwitch: {user} (<https://twitch.tv/{user.login}>){discord}\nSteam: <https://steamcommunity.com/profiles/{steam_id}>"
                                )
                            await self.add_role(member, role)
                            connection._update_tier(db_session, user.tier)
                db_session.commit()

                if not self.settings["pause_bot"]:
                    if connection.twitch_id not in subs_to_return and not self.settings["pause_bot"]:
                        if connection.tier != user.tier:
                            if connection.tier != 0 and (not user.tier or user.tier == 0):
                                subs_to_return[connection.twitch_id] = str(
                                    utils.now() + timedelta(days=int(self.settings["grace_time"]))
                                )
                            else:
                                subs_to_return[connection.twitch_id] = str(
                                    utils.now()
                                )


            if not self.settings["pause_bot"]:
                for sub in queued_subs:  # sub "twitch_id" : date_to_be_removed
                    connection = quick_dict_twitch[sub]
                    time = queued_subs[sub]
                    user = connection.twitch_user
                    if user.tier == connection.tier or (
                        not user.tier and connection.tier == 0
                    ):  # they resubbed before grace ended
                        continue
                    if ":" in time[-5:]:
                        time = f"{time[:-5]}{time[-5:-3]}{time[-2:]}"
                    if datetime.strptime(time, "%Y-%m-%d %H:%M:%S.%f%z") < utils.now():  # must be run now
                        member = self.guild.get_member(int(connection.discord_user_id))
                        if connection.tier > 1:
                            role = roles_allocated[f"tier{connection.tier}_role"]
                            if member and role and role in member.roles:
                                await self.remove_role(member, role)
                            if self.settings["notify_on_unsub"] and self.settings[f"notify_on_tier{connection.tier}"]:
                                discord = await self.get_discord_string(connection.discord_user_id)
                                messages_remove.append(
                                    f"\n\nTier {connection.tier} sub removal notification:\nTwitch: {user} (<https://twitch.tv/{user.login}>){discord}\nSteam: <https://steamcommunity.com/profiles/{connection.steam_id}>"
                                )
                        connection._update_tier(db_session, user.tier)
                    else:
                        subs_to_return[sub] = queued_subs[sub]
                db_session.commit()

            for tier in [2, 3]:
                role = roles_allocated[f"tier{tier}_role"]
                if not role:
                    continue
                for member in role.members:
                    if ignore_role is None or ignore_role not in member.roles:
                        if str(member.id) not in quick_dict_discord:
                            if not self.settings["pause_bot"]:
                                await self.remove_role(member, role)
                        else:
                            connection = quick_dict_discord[str(member.id)]
                            if connection.tier != tier:
                                await self.remove_role(member, role)

        if notify_role:
            for member in notify_role.members:
                return_message = ""
                for message in messages_other:
                    if len(return_message) + len(message) > 1300:
                        await self.private_message(member, return_message)
                        return_message = ""
                    return_message += message
                if return_message != "":
                    await self.private_message(member, return_message)
                    return_message = ""
                for message in messages_remove:
                    if len(return_message) + len(message) > 1300:
                        await self.private_message(member, return_message)
                        return_message = ""
                    return_message += message
                if return_message != "":
                    await self.private_message(member, return_message)
                    return_message = ""
                for message in messages_add:
                    if len(return_message) + len(message) > 1300:
                        await self.private_message(member, return_message)
                        return_message = ""
                    return_message += message
                if return_message != "":
                    await self.private_message(member, return_message)
                    return_message = ""
        self.redis.set("queued-subs-discord", json.dumps(subs_to_return))

    async def run_periodically(self, wait_time, func, *args):
        while True:
            await asyncio.sleep(wait_time)
            if not self.client.is_closed():
                try:
                    await func(*args)
                except Exception as e:
                    log.error(e)

    def schedule_task_periodically(self, wait_time, func, *args):
        return self.private_loop.create_task(self.run_periodically(wait_time, func, *args))

    async def cancel_scheduled_task(self, task):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    def configure(self, settings, start=True):
        self.settings = settings
        if start:
            self._start()

    def _start(self):
        if self.thread:
            self.private_loop.call_soon_threadsafe(self.private_loop.stop)
            self.thread.join()
            self.private_loop = asyncio.get_event_loop()
        self.private_loop.create_task(self.run())
        self.thread = threading.Thread(target=self.run_it_forever)
        self.thread.daemon = True
        self.thread.start()

    def run_it_forever(self):
        self.private_loop.run_forever()

    async def run(self):
        try:
            await self.client.start(self.settings["discord_token"])
        except:
            pass

    def stop(self):
        self.private_loop.create_task(self._stop())

    async def _stop(self):
        log.info("Discord closing")
        await self.cancel_scheduled_task(self.discord_task)
        await self.client.logout()
        try:
            self.client.clear()
        except:
            pass
