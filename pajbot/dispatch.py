import logging
import re

from pajbot.managers.adminlog import AdminLogManager

log = logging.getLogger(__name__)


class Dispatch:
    """
    Methods in this class accessible from commands
    """

    @staticmethod
    def add_win(bot, source, message, event, args):
        # XXX: this is ugly as fuck
        bot.kvi["br_wins"].inc()
        bot.me("{0} added a BR win!".format(source.username))

    @staticmethod
    def add_command(bot, source, message, event, args):
        """Dispatch method for creating commands.
        Usage: !add command ALIAS [options] RESPONSE
        Multiple options available:
        --whisper/--no-whisper
        --reply/--no-reply
        --modonly/--no-modonly
        --cd CD
        --usercd USERCD
        --level LEVEL
        --cost COST
        """

        if message:
            # Make sure we got both an alias and a response
            message_parts = message.split()
            if len(message_parts) < 2:
                bot.whisper(source.username, "Usage: !add command ALIAS [options] RESPONSE")
                return False

            options, response = bot.commands.parse_command_arguments(message_parts[1:])

            options["added_by"] = source.id

            if options is False:
                bot.whisper(source.username, "Invalid command")
                return False

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
                bot.whisper(source.username, "Added your command (ID: {command.id})".format(command=command))

                log_msg = "The !{} command has been created".format(command.command.split("|")[0])
                AdminLogManager.add_entry("Command created", source, log_msg)
                return True

            # At least one alias is already in use, notify the user to use !edit command instead
            bot.whisper(
                source.username,
                "The alias {} is already in use. To edit that command, use !edit command instead of !add command.".format(
                    alias_matched
                ),
            )
            return False

    @staticmethod
    def edit_command(bot, source, message, event, args):
        """Dispatch method for editing commands.
        Usage: !edit command ALIAS [options] RESPONSE
        Multiple options available:
        --whisper/--no-whisper
        --reply/--no-reply
        --modonly/--no-modonly
        --cd CD
        --usercd USERCD
        --level LEVEL
        --cost COST
        """

        if message:
            # Make sure we got both an alias and a response
            message_parts = message.split()
            if len(message_parts) < 2:
                bot.whisper(source.username, "Usage: !add command ALIAS [options] RESPONSE")
                return False

            options, response = bot.commands.parse_command_arguments(message_parts[1:])

            options["edited_by"] = source.id

            if options is False:
                bot.whisper(source.username, "Invalid command")
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
                    source.username,
                    "No command found with the alias {}. Did you mean to create the command? If so, use !add command instead.".format(
                        alias
                    ),
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
            bot.whisper(source.username, "Updated the command (ID: {command.id})".format(command=command))

            if len(new_message) > 0:
                log_msg = 'The !{} command has been updated from "{}" to "{}"'.format(
                    command.command.split("|")[0], old_message, new_message
                )
            else:
                log_msg = "The !{} command has been updated".format(command.command.split("|")[0])

            AdminLogManager.add_entry(
                "Command edited", source, log_msg, data={"old_message": old_message, "new_message": new_message}
            )

    @staticmethod
    def add_funccommand(bot, source, message, event, args):
        """Dispatch method for creating function commands.
        Usage: !add funccommand ALIAS [options] CALLBACK
        Multiple options available:
        --cd CD
        --usercd USERCD
        --level LEVEL
        --cost COST
        --modonly/--no-modonly
        """

        if message:
            # Make sure we got both an alias and a response
            message_parts = message.split(" ")
            if len(message_parts) < 2:
                bot.whisper(source.username, "Usage: !add funccommand ALIAS [options] CALLBACK")
                return False

            options, response = bot.commands.parse_command_arguments(message_parts[1:])

            options["added_by"] = source.id

            if options is False:
                bot.whisper(source.username, "Invalid command")
                return False

            alias_str = message_parts[0].replace("!", "").lower()
            action = {"type": "func", "cb": response.strip()}

            command, new_command, alias_matched = bot.commands.create_command(alias_str, action=action, **options)
            if new_command is True:
                bot.whisper(source.username, "Added your command (ID: {command.id})".format(command=command))
                return True

            # At least one alias is already in use, notify the user to use !edit command instead
            bot.whisper(
                source.username,
                "The alias {} is already in use. To edit that command, use !edit command instead of !add funccommand.".format(
                    alias_matched
                ),
            )
            return False

    @staticmethod
    def edit_funccommand(bot, source, message, event, args):
        """Dispatch method for editing function commands.
        Usage: !edit funccommand ALIAS [options] CALLBACK
        Multiple options available:
        --cd CD
        --usercd USERCD
        --level LEVEL
        --cost COST
        --modonly/--no-modonly
        """

        if message:
            # Make sure we got both an alias and a response
            message_parts = message.split(" ")
            if len(message_parts) < 2:
                bot.whisper(source.username, "Usage: !add funccommand ALIAS [options] CALLBACK")
                return False

            options, response = bot.commands.parse_command_arguments(message_parts[1:])

            options["edited_by"] = source.id

            if options is False:
                bot.whisper(source.username, "Invalid command")
                return False

            alias = message_parts[0].replace("!", "").lower()
            action = {"type": "func", "cb": response.strip()}

            command = bot.commands.get(alias, None)

            if command is None:
                bot.whisper(
                    source.username,
                    "No command found with the alias {}. Did you mean to create the command? If so, use !add funccommand instead.".format(
                        alias
                    ),
                )
                return False

            if len(action["cb"]) > 0:
                options["action"] = action
            bot.commands.edit_command(command, **options)
            bot.whisper(source.username, "Updated the command (ID: {command.id})".format(command=command))

    @staticmethod
    def remove_win(bot, source, message, event, args):
        # XXX: This is also ugly as fuck
        bot.kvi["br_wins"].dec()
        bot.me("{0} removed a BR win!".format(source.username))

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
                bot.whisper(source.username, "Usage: !add alias existingalias newalias")
                return False

            existing_alias = message_parts[0]
            new_aliases = re.split(r"\|| ", " ".join(message_parts[1:]))
            added_aliases = []
            already_used_aliases = []

            if existing_alias not in bot.commands:
                bot.whisper(source.username, 'No command called "{0}" found'.format(existing_alias))
                return False

            command = bot.commands[existing_alias]

            # error out on commands that are not from the DB, e.g. module commands like !8ball that cannot have
            # aliases registered. (command.command and command.data are None on those commands)
            if command.data is None or command.command is None:
                bot.whisper(source.username, "That command cannot have aliases added to.")
                return False

            for alias in set(new_aliases):
                if alias in bot.commands:
                    already_used_aliases.append(alias)
                else:
                    added_aliases.append(alias)
                    bot.commands[alias] = command

            if len(added_aliases) > 0:
                new_aliases = "{}|{}".format(command.command, "|".join(added_aliases))
                bot.commands.edit_command(command, command=new_aliases)

                bot.whisper(
                    source.username,
                    "Successfully added the aliases {0} to {1}".format(", ".join(added_aliases), existing_alias),
                )
                log_msg = "The aliases {0} has been added to {1}".format(", ".join(added_aliases), existing_alias)
                AdminLogManager.add_entry("Alias added", source, log_msg)
            if len(already_used_aliases) > 0:
                bot.whisper(
                    source.username,
                    "The following aliases were already in use: {0}".format(", ".join(already_used_aliases)),
                )
        else:
            bot.whisper(source.username, "Usage: !add alias existingalias newalias")

    @staticmethod
    def remove_alias(bot, source, message, event, args):
        """Dispatch method for removing aliases from a command.
        Usage: !remove alias EXISTING_ALIAS_1 EXISTING_ALIAS_2"""
        if message:
            aliases = re.split(r"\|| ", message.lower())
            log.info(aliases)
            if len(aliases) < 1:
                bot.whisper(source.username, "Usage: !remove alias EXISTINGALIAS")
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
                    bot.whisper(source.username, "That command cannot have aliases removed from.")
                    return False

                current_aliases = command.command.split("|")
                current_aliases.remove(alias)

                if len(current_aliases) == 0:
                    bot.whisper(
                        source.username,
                        "{0} is the only remaining alias for this command and can't be removed.".format(alias),
                    )
                    continue

                new_aliases = "|".join(current_aliases)
                bot.commands.edit_command(command, command=new_aliases)

                num_removed += 1
                del bot.commands[alias]
                log_msg = "The alias {0} has been removed from {1}".format(alias, new_aliases.split("|")[0])
                AdminLogManager.add_entry("Alias removed", source, log_msg)

            whisper_str = ""
            if num_removed > 0:
                whisper_str = "Successfully removed {0} aliases.".format(num_removed)
            if len(commands_not_found) > 0:
                whisper_str += " Aliases {0} not found".format(", ".join(commands_not_found))
            if len(whisper_str) > 0:
                bot.whisper(source.username, whisper_str)
        else:
            bot.whisper(source.username, "Usage: !remove alias EXISTINGALIAS")

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
                bot.whisper(source.username, "No command with the given parameters found")
                return False

            if command.id == -1:
                bot.whisper(source.username, "That command is an internal command, it cannot be removed.")
                return False

            if source.level < 2000:
                if command.action is not None and not command.action.type == "message":
                    bot.whisper(source.username, "That command is not a normal command, it cannot be removed by you.")
                    return False

            bot.whisper(source.username, "Successfully removed command with id {0}".format(command.id))
            log_msg = "The !{} command has been removed".format(command.command.split("|")[0])
            AdminLogManager.add_entry("Command removed", source, log_msg)
            bot.commands.remove_command(command)
        else:
            bot.whisper(source.username, "Usage: !remove command (COMMAND_ID|COMMAND_ALIAS)")

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
            username = message.split(" ")[0].strip().lower()
            user = bot.users.find(username)
        else:
            user = source

        if user:
            if user.subscriber:
                bot.say("{0} is a subscriber PogChamp".format(user.username))
            else:
                bot.say("{0} is not a subscriber FeelsBadMan".format(user.username))
        else:
            bot.say("{0} was not found in the user database".format(username))

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
        extra_message = "{0}, your reminder from {1} seconds ago is over: {2}".format(
            source.username_raw, delay, reminder_text
        )

        bot.say(
            "{0}, I will remind you of '{2}' in {1} seconds. SeemsGood".format(
                source.username_raw, delay, reminder_text
            )
        )
        bot.execute_delayed(delay, bot.say, (extra_message,))

    @staticmethod
    def twitter_follow(bot, source, message, event, args):
        # XXX: This should be a module
        if message:
            username = message.split(" ")[0].strip().lower()
            if bot.twitter_manager.follow_user(username):
                bot.whisper(source.username, "Now following {}".format(username))
            else:
                bot.whisper(
                    source.username,
                    "An error occured while attempting to follow {}, perhaps we are already following this person?".format(
                        username
                    ),
                )

    @staticmethod
    def twitter_unfollow(bot, source, message, event, args):
        # XXX: This should be a module
        if message:
            username = message.split(" ")[0].strip().lower()
            if bot.twitter_manager.unfollow_user(username):
                bot.whisper(source.username, "No longer following {}".format(username))
            else:
                bot.whisper(
                    source.username,
                    "An error occured while attempting to unfollow {}, perhaps we are not following this person?".format(
                        username
                    ),
                )
