import logging
import re

from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import DBManager
from pajbot.models.user import User

log = logging.getLogger(__name__)


class Dispatch:
    """
    Methods in this class accessible from commands
    """

    @staticmethod
    def add_win(bot, source, message, event, args):
        # XXX: this is ugly as fuck
        bot.kvi["br_wins"].inc()
        bot.me(f"{source} added a BR win!")

    @staticmethod
    def add_command(bot, source, message, event, args):
        """Dispatch method for creating commands.
        Usage: !add command ALIAS [options] RESPONSE
        See pajbot/managers/command.py parse_command_arguments for available options
        """

        if not message:
            return False

        # Make sure we got both an alias and a response
        message_parts = message.split()
        if len(message_parts) < 2:
            bot.whisper(source, "Usage: !add command ALIAS [options] RESPONSE")
            return False

        options, response = bot.commands.parse_command_arguments(message_parts[1:])

        if options is False:
            bot.whisper(source, "Invalid command")
            return False

        options["added_by"] = source.id

        alias_str = message_parts[0].replace("!", "").lower()
        type = "say"
        if options["whisper"] is True:
            type = "whisper"
        elif options["reply"] is True:
            type = "reply"
        elif response.startswith("/me") or response.startswith(".me"):
            type = "me"
            response = " ".join(response.split(" ")[1:])
        elif options["whisper"] is False or options["reply"] is False:
            type = "say"
        action = {"type": type, "message": response}

        command, new_command, alias_matched = bot.commands.create_command(alias_str, action=action, **options)
        if new_command is True:
            bot.whisper(source, f"Added your command (ID: {command.id})")

            log_msg = f"The !{command.command.split('|')[0]} command has been created"
            AdminLogManager.add_entry("Command created", source, log_msg)
            return True

        # At least one alias is already in use, notify the user to use !edit command instead
        bot.whisper(
            source,
            f"The alias {alias_matched} is already in use. To edit that command, use !edit command instead of !add command.",
        )
        return False

    @staticmethod
    def edit_command(bot, source, message, event, args):
        """Dispatch method for editing commands.
        Usage: !edit command ALIAS [options] RESPONSE
        See pajbot/managers/command.py parse_command_arguments for available options
        """

        if message:
            # Make sure we got both an alias and a response
            message_parts = message.split()
            if len(message_parts) < 2:
                bot.whisper(source, "Usage: !add command ALIAS [options] RESPONSE")
                return False

            options, response = bot.commands.parse_command_arguments(message_parts[1:])

            options["edited_by"] = source.id

            if options is False:
                bot.whisper(source, "Invalid command")
                return False

            alias = message_parts[0].replace("!", "").lower()
            type = "say"
            if options["whisper"] is True:
                type = "whisper"
            elif options["reply"] is True:
                type = "reply"
            elif response.startswith("/me") or response.startswith(".me"):
                type = "me"
                response = " ".join(response.split(" ")[1:])
            elif options["whisper"] is False or options["reply"] is False:
                type = "say"
            action = {"type": type, "message": response}

            command = bot.commands.get(alias, None)

            if command is None:
                bot.whisper(
                    source,
                    f"No command found with the alias {alias}. Did you mean to create the command? If so, use !add command instead.",
                )
                return False

            old_message = ""
            new_message = ""

            if len(action["message"]) > 0:
                options["action"] = action
                old_message = command.action.response
                new_message = action["message"]
            elif not type == command.action.subtype:
                options["action"] = {"type": type, "message": command.action.response}
            bot.commands.edit_command(command, **options)
            bot.whisper(source, f"Updated the command (ID: {command.id})")

            if len(new_message) > 0:
                log_msg = f'The !{command.command.split("|")[0]} command has been updated from "{old_message}" to "{new_message}"'
            else:
                log_msg = f"The !{command.command.split('|')[0]} command has been updated"

            AdminLogManager.add_entry(
                "Command edited", source, log_msg, data={"old_message": old_message, "new_message": new_message}
            )

    @staticmethod
    def add_funccommand(bot, source, message, event, args):
        """Dispatch method for creating function commands.
        Usage: !add funccommand ALIAS [options] CALLBACK
        See pajbot/managers/command.py parse_command_arguments for available options
        """

        if message:
            # Make sure we got both an alias and a response
            message_parts = message.split(" ")
            if len(message_parts) < 2:
                bot.whisper(source, "Usage: !add funccommand ALIAS [options] CALLBACK")
                return False

            options, response = bot.commands.parse_command_arguments(message_parts[1:])

            options["added_by"] = source.id

            if options is False:
                bot.whisper(source, "Invalid command")
                return False

            alias_str = message_parts[0].replace("!", "").lower()
            action = {"type": "func", "cb": response.strip()}

            command, new_command, alias_matched = bot.commands.create_command(alias_str, action=action, **options)
            if new_command is True:
                bot.whisper(source, f"Added your command (ID: {command.id})")
                return True

            # At least one alias is already in use, notify the user to use !edit command instead
            bot.whisper(
                source,
                f"The alias {alias_matched} is already in use. To edit that command, use !edit command instead of !add funccommand.",
            )
            return False

    @staticmethod
    def edit_funccommand(bot, source, message, event, args):
        """Dispatch method for editing function commands.
        Usage: !edit funccommand ALIAS [options] CALLBACK
        See pajbot/managers/command.py parse_command_arguments for available options
        """

        if message:
            # Make sure we got both an alias and a response
            message_parts = message.split(" ")
            if len(message_parts) < 2:
                bot.whisper(source, "Usage: !add funccommand ALIAS [options] CALLBACK")
                return False

            options, response = bot.commands.parse_command_arguments(message_parts[1:])

            options["edited_by"] = source.id

            if options is False:
                bot.whisper(source, "Invalid command")
                return False

            alias = message_parts[0].replace("!", "").lower()
            action = {"type": "func", "cb": response.strip()}

            command = bot.commands.get(alias, None)

            if command is None:
                bot.whisper(
                    source,
                    f"No command found with the alias {alias}. Did you mean to create the command? If so, use !add funccommand instead.",
                )
                return False

            if len(action["cb"]) > 0:
                options["action"] = action
            bot.commands.edit_command(command, **options)
            bot.whisper(source, f"Updated the command (ID: {command.id})")

    @staticmethod
    def remove_win(bot, source, message, event, args):
        # XXX: This is also ugly as fuck
        bot.kvi["br_wins"].dec()
        bot.me(f"{source} removed a BR win!")

    @staticmethod
    def add_alias(bot, source, message, event, args):
        """Dispatch method for adding aliases to already-existing commands.
        Usage: !add alias EXISTING_ALIAS NEW_ALIAS_1 NEW_ALIAS_2 ...
        """

        if message:
            message = message.replace("!", "").lower()
            # Make sure we got both an existing alias and at least one new alias
            message_parts = message.split()
            if len(message_parts) < 2:
                bot.whisper(source, "Usage: !add alias existingalias newalias")
                return False

            existing_alias = message_parts[0]
            new_aliases = re.split(r"\|| ", " ".join(message_parts[1:]))
            added_aliases = []
            already_used_aliases = []

            if existing_alias not in bot.commands:
                bot.whisper(source, f'No command called "{existing_alias}" found')
                return False

            command = bot.commands[existing_alias]

            # error out on commands that are not from the DB, e.g. module commands like !8ball that cannot have
            # aliases registered. (command.command and command.data are None on those commands)
            if command.data is None or command.command is None:
                bot.whisper(source, "That command cannot have aliases added to.")
                return False

            for alias in set(new_aliases):
                if alias in bot.commands:
                    already_used_aliases.append(alias)
                else:
                    added_aliases.append(alias)
                    bot.commands[alias] = command

            if len(added_aliases) > 0:
                new_aliases = f"{command.command}|{'|'.join(added_aliases)}"
                bot.commands.edit_command(command, command=new_aliases)

                bot.whisper(source, f"Successfully added the aliases {', '.join(added_aliases)} to {existing_alias}")
                log_msg = f"The aliases {', '.join(added_aliases)} has been added to {existing_alias}"
                AdminLogManager.add_entry("Alias added", source, log_msg)
            if len(already_used_aliases) > 0:
                bot.whisper(source, f"The following aliases were already in use: {', '.join(already_used_aliases)}")
        else:
            bot.whisper(source, "Usage: !add alias existingalias newalias")

    @staticmethod
    def remove_alias(bot, source, message, event, args):
        """Dispatch method for removing aliases from a command.
        Usage: !remove alias EXISTING_ALIAS_1 EXISTING_ALIAS_2"""
        if message:
            aliases = re.split(r"\|| ", message.lower())
            log.info(aliases)
            if len(aliases) < 1:
                bot.whisper(source, "Usage: !remove alias EXISTINGALIAS")
                return False

            num_removed = 0
            commands_not_found = []
            for alias in aliases:
                if alias not in bot.commands:
                    commands_not_found.append(alias)
                    continue

                command = bot.commands[alias]

                # error out on commands that are not from the DB, e.g. module commands like !8ball that cannot have
                # aliases registered. (command.command and command.data are None on those commands)
                if command.data is None or command.command is None:
                    bot.whisper(source, "That command cannot have aliases removed from.")
                    return False

                current_aliases = command.command.split("|")
                current_aliases.remove(alias)

                if len(current_aliases) == 0:
                    bot.whisper(source, f"{alias} is the only remaining alias for this command and can't be removed.")
                    continue

                new_aliases = "|".join(current_aliases)
                bot.commands.edit_command(command, command=new_aliases)

                num_removed += 1
                del bot.commands[alias]
                log_msg = f"The alias {alias} has been removed from {new_aliases.split('|')[0]}"
                AdminLogManager.add_entry("Alias removed", source, log_msg)

            whisper_str = ""
            if num_removed > 0:
                whisper_str = f"Successfully removed {num_removed} aliases."
            if len(commands_not_found) > 0:
                whisper_str += f" Aliases {', '.join(commands_not_found)} not found"
            if len(whisper_str) > 0:
                bot.whisper(source, whisper_str)
        else:
            bot.whisper(source, "Usage: !remove alias EXISTINGALIAS")

    @staticmethod
    def remove_command(bot, source, message, event, args):
        if message:
            id = None
            command = None
            try:
                id = int(message)
            except Exception:
                pass

            if id is None:
                potential_cmd = "".join(message.split(" ")[:1]).lower().replace("!", "")
                if potential_cmd in bot.commands:
                    command = bot.commands[potential_cmd]
            else:
                for key, check_command in bot.commands.items():
                    if check_command.id == id:
                        command = check_command
                        break

            if command is None:
                bot.whisper(source, "No command with the given parameters found")
                return False

            if command.id == -1:
                bot.whisper(source, "That command is an internal command, it cannot be removed.")
                return False

            if source.level < 2000:
                if command.action is not None and not command.action.type == "message":
                    bot.whisper(source, "That command is not a normal command, it cannot be removed by you.")
                    return False

            bot.whisper(source, f"Successfully removed command with id {command.id}")
            log_msg = f"The !{command.command.split('|')[0]} command has been removed"
            AdminLogManager.add_entry("Command removed", source, log_msg)
            bot.commands.remove_command(command)
        else:
            bot.whisper(source, "Usage: !remove command (COMMAND_ID|COMMAND_ALIAS)")

    @staticmethod
    def tweet(bot, source, message, event, args):
        if message and len(message) > 1:
            try:
                log.info("sending tweet: %s", message[:140])
                bot.twitter_manager.twitter_client.update_status(status=message)
            except Exception:
                log.exception("Caught an exception")

    @staticmethod
    def eval(bot, source, message, event, args):
        if not bot.dev:
            return

        if not message:
            return

        try:
            exec(message)
        except:
            log.exception('Exception caught while trying to evaluate code: "%s"', message)

    @staticmethod
    def check_sub(bot, source, message, event, args):
        if message:
            input = message.split(" ")[0]
            with DBManager.create_session_scope(expire_on_commit=False) as db_session:
                user = User.find_by_user_input(db_session, input)

                if user is None:
                    bot.say(f"That user was not found in the user database")
        else:
            user = source

        if user.subscriber:
            bot.say(f"{user} is a subscriber PogChamp")
        else:
            bot.say(f"{user} is not a subscriber FeelsBadMan")

    @staticmethod
    def remindme(bot, source, message, event, args):
        if not message:
            return False

        parts = message.split(" ")
        if len(parts) < 1:
            # Not enough arguments
            return False

        delay = int(parts[0])
        reminder_text = " ".join(parts[1:]).strip()
        extra_message = f"{source}, your reminder from {delay} seconds ago is over: {reminder_text}"

        bot.say(f"{source}, I will remind you of '{reminder_text}' in {delay} seconds. SeemsGood")
        bot.execute_delayed(delay, bot.say, extra_message)

    @staticmethod
    def twitter_follow(bot, source, message, event, args):
        # XXX: This should be a module
        if message:
            username = message.split(" ")[0].strip().lower()
            if bot.twitter_manager.follow_user(username):
                bot.whisper(source, f"Now following {username}")
            else:
                bot.whisper(
                    source,
                    f"An error occured while attempting to follow {username}, perhaps we are already following this person?",
                )

    @staticmethod
    def twitter_unfollow(bot, source, message, event, args):
        # XXX: This should be a module
        if message:
            username = message.split(" ")[0].strip().lower()
            if bot.twitter_manager.unfollow_user(username):
                bot.whisper(source, f"No longer following {username}")
            else:
                bot.whisper(
                    source,
                    f"An error occured while attempting to unfollow {username}, perhaps we are not following this person?",
                )
