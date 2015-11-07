import math
import re
import logging
import collections
import argparse

from tyggbot.models.user import User
from tyggbot.models.filter import Filter
from tyggbot.tbutil import time_limit, TimeoutException

from sqlalchemy import desc
from sqlalchemy import func

log = logging.getLogger('tyggbot')


class Dispatch:
    """
    Methods in this class accessible from commands
    """

    def nl(tyggbot, source, message, event, args):
        if message:
            tmp_username = message.split(' ')[0].strip().lower()
            user = tyggbot.users.find(tmp_username)
            if user:
                username = user.username_raw
                num_lines = user.num_lines
            else:
                username = tmp_username
                num_lines = 0
        else:
            username = source.username_raw
            num_lines = source.num_lines

        phrase_data = {
                'username': username,
                'num_lines': num_lines
                }

        if num_lines > 0:
            tyggbot.say(tyggbot.phrases['nl'].format(**phrase_data))
        else:
            tyggbot.say(tyggbot.phrases['nl_0'].format(**phrase_data))

    def point_pos(tyggbot, source, message, event, args):
        user = None

        if message:
            tmp_username = message.split(' ')[0].strip().lower()
            user = tyggbot.users.find(tmp_username)

        if not user:
            user = source

        phrase_data = {
                'points': user.points
                }

        if user == source:
            phrase_data['username_w_verb'] = 'You are'
        else:
            phrase_data['username_w_verb'] = '{0} is'.format(user.username_raw)

        if user.points > 0:
            query_data = tyggbot.users.db_session.query(func.count(User.id)).filter(User.points > user.points).one()
            phrase_data['point_pos'] = int(query_data[0]) + 1
            tyggbot.whisper(source.username, tyggbot.phrases['point_pos'].format(**phrase_data))

    def nl_pos(tyggbot, source, message, event, args):
        if message:
            tmp_username = message.split(' ')[0].strip().lower()
            user = tyggbot.users.find(tmp_username)
            if user:
                username = user.username_raw
                num_lines = user.num_lines
            else:
                username = tmp_username
                num_lines = 0
        else:
            username = source.username_raw
            num_lines = source.num_lines

        phrase_data = {
                'username': username,
                'num_lines': num_lines
                }

        if num_lines <= 0:
            tyggbot.say(tyggbot.phrases['nl_0'].format(**phrase_data))
        else:
            query_data = tyggbot.users.db_session.query(func.count(User.id)).filter(User.num_lines > user.num_lines).one()
            phrase_data['nl_pos'] = int(query_data[0]) + 1
            tyggbot.say(tyggbot.phrases['nl_pos'].format(**phrase_data))

    def query(tyggbot, source, message, event, args):
        if tyggbot.wolfram is None:
            return False

        try:
            log.debug('Querying wolfram "{0}"'.format(message))
            res = tyggbot.wolfram.query(message)

            x = 0
            for pod in res.pods:
                if x == 1:
                    res = '{0}'.format(' '.join(pod.text.splitlines()).strip())
                    log.debug('Answering with {0}'.format(res))
                    tyggbot.say(res)
                    break

                x = x + 1
        except Exception as e:
            log.error('caught exception: {0}'.format(e))

    def math(tyggbot, source, message, event, args):
        if message:
            message = message.replace('pi', str(math.pi))
            message = message.replace('e', str(math.e))
            message = message.replace('π', str(math.pi))
            message = message.replace('^', '**')
            message = message.replace(',', '.')
            res = '??'
            expr_res = None

            emote = 'Kappa'

            try:
                with time_limit(1):
                    expr_res = tyggbot.tbm.eval_expr(''.join(message))
                    if expr_res == 69 or expr_res == 69.69:
                        emote = 'Kreygasm'
                    elif expr_res == 420 or expr_res == 420.0:
                        emote = 'CiGrip'
                    res = '{2}, {0} {1}'.format(expr_res, emote, source.username)
            except TimeoutException as e:
                res = 'timed out DansGame'
                log.error('Timeout exception: {0}'.format(e))
            except Exception as e:
                log.error('Uncaught exception: {0}'.format(e))
                return

            tyggbot.say(res)

    def multi(tyggbot, source, message, event, args):
        if message:
            streams = message.strip().split(' ')
            if len(streams) == 1:
                streams.insert(0, tyggbot.streamer)

            url = 'http://multitwitch.tv/' + '/'.join(streams)

            tyggbot.say('{0}, {1}'.format(source.username, url))

    def ab(tyggbot, source, message, event, args):
        if message:
            message = re.sub(' +', ' ', message)

            msg_parts = message.split(' ')
            if len(msg_parts) >= 2:
                s = ''
                for c in msg_parts[1]:
                    s += msg_parts[0] + ' ' + c + ' '
                s += msg_parts[0]

                tyggbot.say('{0}, {1}'.format(source.username, s))

                return True

        return False

    def abc(tyggbot, source, message, event, args):
        if message:
            message = re.sub(' +', ' ', message)

            msg_parts = message.split(' ')
            if len(msg_parts) >= 3:
                s = ''
                for msg in msg_parts[1:]:
                    s += msg_parts[0] + ' ' + msg + ' '
                s += msg_parts[0]

                tyggbot.say('{0}, {1}'.format(source.username, s))

                return True

        return False

    def silence(tyggbot, source, message, event, args):
        tyggbot.silent = True

    def unsilence(tyggbot, source, message, event, args):
        tyggbot.silent = False

    def add_banphrase(tyggbot, source, message, event, args):
        if message:
            parser = argparse.ArgumentParser()
            # parser.add_argument('--whisper', dest='whisper', action='store_true')
            parser.add_argument('--length', type=int)
            parser.add_argument('--notify', dest='notify', action='store_true')
            parser.set_defaults(length=Filter.DEFAULT_TIMEOUT_LENGTH, notify=False)

            try:
                args, unknown = parser.parse_known_args(message.split())
            except SystemExit:
                tyggbot.whisper(source.username, 'Invalid banphrase')
                return False
            except:
                log.exception('Unhandled exception in add_banphrase')
                return False

            options = vars(args)
            options['extra_args'] = {
                    'notify': options['notify'],
                    'time': options['length'],
                    }
            banphrase = ' '.join(unknown)
            if len(banphrase) == 0:
                tyggbot.whisper(source.username, 'No banphrase given')
                return False

            filter, new_filter = tyggbot.filters.add_banphrase(banphrase, **options)

            if new_filter is True:
                tyggbot.whisper(source.username, 'Inserted your banphrase (ID: {filter.id})'.format(filter=filter))
                return True

            filter.set(**options)
            tyggbot.whisper(source.username, 'Updated the given banphrase')

    def add_win(tyggbot, source, message, event, args):
        tyggbot.kvi['br_wins'].inc()
        tyggbot.me('{0} added a BR win!'.format(source.username))
        log.debug('{0} added a BR win!'.format(source.username))

    def add_command(tyggbot, source, message, event, args):
        """Dispatch method for creating and editing commands.
        Usage: !add command ALIAS [options] RESPONSE
        Multiple options available:
        --whisper
        --cd CD
        --usercd USERCD
        --level LEVEL
        """

        if message:
            # Make sure we got both an alias and a response
            message_parts = message.split()
            if len(message_parts) < 2:
                tyggbot.whisper(source.username, 'Usage: !add command ALIAS [options] RESPONSE')
                return False

            options, response = tyggbot.commands.parse_command_arguments(message_parts[1:])

            if options is False:
                tyggbot.whisper(source.username, 'Invalid command')
                return False

            alias_str = message_parts[0]
            type = 'say'
            if options['whisper'] is True:
                type = 'whisper'
            elif response.startswith('/me') or response.startswith('.me'):
                type = 'me'
            action = {
                    'type': type,
                    'message': response,
                    }

            command, new_command = tyggbot.commands.create_command(alias_str, action=action)
            if new_command is True:
                tyggbot.whisper(source.username, 'Added your command (ID: {command.id})'.format(command=command))
                return True

            if len(action['message']) > 0:
                options['action'] = action
            command.set(**options)
            tyggbot.whisper(source.username, 'Updated the command (ID: {command.id})'.format(command=command))

    def add_funccommand(tyggbot, source, message, event, args):
        """Dispatch method for creating and editing function commands.
        Usage: !add command ALIAS [options] CALLBACK
        Multiple options available:
        --whisper
        --cd CD
        --usercd USERCD
        --level LEVEL
        """
        if message:
            # Make sure we got both an alias and a response
            message_parts = message.split(' ')
            if len(message_parts) < 2:
                tyggbot.whisper(source.username, 'Usage: !add funccommand ALIAS [options] CALLBACK')
                return False

            options, response = tyggbot.commands.parse_command_arguments(message_parts[1:])

            if options is False:
                tyggbot.whisper(source.username, 'Invalid command')
                return False

            alias_str = message_parts[0]
            action = {
                    'type': 'func',
                    'cb': response.strip(),
                    }

            command, new_command = tyggbot.commands.create_command(alias_str, action=action)
            if new_command is True:
                tyggbot.whisper(source.username, 'Added your command (ID: {command.id})'.format(command=command))
                return True

            if len(action['message']) > 0:
                options['action'] = action
            command.set(**options)
            tyggbot.whisper(source.username, 'Updated the command (ID: {command.id})'.format(command=command))

    def remove_banphrase(tyggbot, source, message, event, args):
        if message:
            id = None
            filter = None
            try:
                id = int(message)
            except Exception:
                pass

            if id is not None:
                filter = tyggbot.filters.get(id=id)
            else:
                filter = tyggbot.filters.get(phrase=message)

            if filter is None:
                tyggbot.whisper(source.username, 'No banphrase with the given parameters found')
                return False

            tyggbot.whisper(source.username, 'Successfully removed banphrase with id {0}'.format(filter.id))
            tyggbot.filters.remove_filter(filter)
        else:
            tyggbot.whisper(source.username, 'Usage: !remove banphrase (BANPHRASE_ID)')
            return False

    def remove_win(tyggbot, source, message, event, args):
        tyggbot.kvi['br_wins'].dec()
        tyggbot.me('{0} removed a BR win!'.format(source.username))
        log.debug('{0} removed a BR win!'.format(source.username))

    def add_alias(tyggbot, source, message, event, args):
        """Dispatch method for adding aliases to already-existing commands.
        Usage: !add alias EXISTING_ALIAS NEW_ALIAS_1 NEW_ALIAS_2 ...
        """

        if message:
            # Make sure we got both an existing alias and at least one new alias
            message_parts = message.split()
            if len(message_parts) < 2:
                tyggbot.whisper(source.username, "Usage: !add alias existingalias newalias")
                return False

            existing_alias = message_parts[0]
            new_aliases = re.split('\|| ', ' '.join(message_parts[1:]))
            added_aliases = []
            already_used_aliases = []

            if existing_alias not in tyggbot.commands:
                tyggbot.whisper(source.username, 'No command called "{0}" found'.format(existing_alias))
                return False

            command = tyggbot.commands[existing_alias]

            for alias in set(new_aliases):
                if alias in tyggbot.commands:
                    already_used_aliases.append(alias)
                else:
                    added_aliases.append(alias)
                    tyggbot.commands[alias] = command

            if len(added_aliases) > 0:
                command.command += '|' + '|'.join(added_aliases)
                tyggbot.whisper(source.username, 'Successfully added the aliases {0} to {1}'.format(', '.join(added_aliases), existing_alias))
            if len(already_used_aliases) > 0:
                tyggbot.whisper(source.username, 'The following aliases were already in use: {0}'.format(', '.join(already_used_aliases)))
        else:
            tyggbot.whisper(source.username, "Usage: !add alias existingalias newalias")

    def remove_alias(tyggbot, source, message, event, args):
        """Dispatch method for removing aliases from a command.
        Usage: !remove alias EXISTING_ALIAS_1 EXISTING_ALIAS_2"""
        if message:
            aliases = re.split('\|| ', message.lower())
            log.info(aliases)
            if len(aliases) < 1:
                tyggbot.whisper(source.username, "Usage: !remove alias EXISTINGALIAS")
                return False

            num_removed = 0
            commands_not_found = []
            for alias in aliases:
                if alias not in tyggbot.commands:
                    commands_not_found.append(alias)
                    continue

                command = tyggbot.commands[alias]

                current_aliases = command.command.split('|')
                current_aliases.remove(alias)

                if len(current_aliases) == 0:
                    tyggbot.whisper(source.username, "{0} is the only remaining alias for this command and can't be removed.".format(alias))
                    continue

                command.command = '|'.join(current_aliases)
                num_removed += 1
                del tyggbot.commands[alias]

            whisper_str = ''
            if num_removed > 0:
                whisper_str = 'Successfully removed {0} aliases.'.format(num_removed)
            if len(commands_not_found) > 0:
                whisper_str += ' Aliases {0} not found'.format(', '.join(commands_not_found))
            if len(whisper_str) > 0:
                tyggbot.whisper(source.username, whisper_str)
        else:
            tyggbot.whisper(source.username, "Usage: !remove alias EXISTINGALIAS")

    def remove_command(tyggbot, source, message, event, args):
        if message:
            id = None
            command = None
            try:
                id = int(message)
            except Exception:
                pass

            if id is None:
                potential_cmd = ''.join(message.split(' ')[:1]).lower()
                if potential_cmd in tyggbot.commands:
                    command = tyggbot.commands[potential_cmd]
                    log.info('got command: {0}'.format(command))
            else:
                for key, check_command in tyggbot.commands.items():
                    if check_command.id == id:
                        command = check_command
                        break

            if command is None:
                tyggbot.whisper(source.username, 'No command with the given parameters found')
                return False

            if (not command.action.type == 'message' and source.level < 2000) or command.id == -1:
                tyggbot.whisper(source.username, 'That command is not a normal command, it cannot be removed by you.')
                return False

            tyggbot.whisper(source.username, 'Successfully removed command with id {0}'.format(command.id))
            tyggbot.commands.remove_command(command)
        else:
            tyggbot.whisper(source.username, 'Usage: !remove command (COMMAND_ID|COMMAND_ALIAS)')

    def add_link(tyggbot, source, message, event, args):
        parts = message.split(' ')
        if parts[0] not in ['blacklist', 'whitelist']:
            tyggbot.whisper(source.username, 'Usage !add link whitelist|blacklist (level of blacklisting, default is 1) http://yourlink.com secondlink.com http://this.org/banned_path/')
            return

        try:
            if parts[0] == 'blacklist':
                if not parts[1].isnumeric():
                    for link in parts[1:]:
                        tyggbot.link_checker.blacklist_url(link)
                else:
                    for link in parts[2:]:
                        tyggbot.link_checker.blacklist_url(link, level=int(parts[1]))
            if parts[0] == 'whitelist':
                for link in parts[1:]:
                    tyggbot.link_checker.whitelist_url(link)
        except:
            log.exception("Unhandled exception in add_link")
            tyggbot.whisper(source.username, "Some error occurred white adding your links")

        tyggbot.whisper(source.username, 'Successfully added your links')

    def remove_link(tyggbot, source, message, event, args):
        parts = message.split(' ')
        if parts[0] not in ['blacklist', 'whitelist']:
            tyggbot.whisper(source.username, 'Usage !remove link whitelist|blacklist http://yourlink.com secondlink.com http://this.org/banned_path/')
            return

        try:
            for link in parts[1:]:
                tyggbot.link_checker.unlist_url(link, parts[0])
        except:
            log.exception("Unhandled exception in add_link")
            tyggbot.whisper(source.username, "Some error occurred white adding your links")

        tyggbot.whisper(source.username, 'Successfully removed your links')

    def debug_command(tyggbot, source, message, event, args):
        if message and len(message) > 0:
            try:
                id = int(message)
            except Exception:
                id = -1

            command = False

            if id == -1:
                potential_cmd = ''.join(message.split(' ')[:1]).lower()
                if potential_cmd in tyggbot.commands:
                    command = tyggbot.commands[potential_cmd]
            else:
                for key, potential_cmd in tyggbot.commands.items():
                    if potential_cmd.id == id:
                        command = potential_cmd
                        break

            if not command:
                tyggbot.whisper(source.username, 'No command with found with the given parameters.')
                return False

            data = collections.OrderedDict()
            data['id'] = command.id
            data['level'] = command.level
            data['type'] = command.action.type
            data['cost'] = command.cost
            data['cd_all'] = command.delay_all
            data['cd_user'] = command.delay_user

            if command.action.type == 'message':
                data['response'] = command.action.response
            elif command.action.type == 'func' or command.action.type == 'rawfunc':
                data['cb'] = command.action.cb.__name__

            tyggbot.whisper(source.username, ', '.join(['%s=%s' % (key, value) for (key, value) in data.items()]))
        else:
            tyggbot.whisper(source.username, 'Usage: !debug command (COMMAND_ID|COMMAND_ALIAS)')

    def debug_user(tyggbot, source, message, event, args):
        if message and len(message) > 0:
            username = message.split(' ')[0].strip().lower()
            user = tyggbot.users[username]

            if user.id == -1:
                del tyggbot.users[username]
                tyggbot.whisper(source.username, 'No user with this username found.')
                return False

            data = collections.OrderedDict()
            data['id'] = user.id
            data['level'] = user.level
            data['num_lines'] = user.num_lines
            data['points'] = user.points
            data['last_seen'] = user.last_seen
            data['last_active'] = user.last_active

            tyggbot.whisper(source.username, ', '.join(['%s=%s' % (key, value) for (key, value) in data.items()]))
        else:
            tyggbot.whisper(source.username, 'Usage: !debug user USERNAME')

    def level(tyggbot, source, message, event, args):
        if message:
            msg_args = message.split(' ')
            if len(msg_args) > 1:
                username = msg_args[0].lower()
                new_level = int(msg_args[1])
                if new_level >= source.level:
                    tyggbot.whisper(source.username, 'You cannot promote someone to the same or higher level as you ({0}).'.format(source.level))
                    return False

                user = tyggbot.users.find(username)

                if not user:
                    tyggbot.whisper(source.username, 'No user with that name found.')
                    return False

                user.level = new_level
                user.needs_sync = True

                tyggbot.whisper(source.username, '{0}\'s user level set to {1}'.format(username, new_level))

                return True

        tyggbot.whisper(source.username, 'Usage: !level USERNAME NEW_LEVEL')
        return False

    def say(tyggbot, source, message, event, args):
        if message:
            tyggbot.say(message)

    def whisper(tyggbot, source, message, event, args):
        if message:
            msg_args = message.split(' ')
            if len(msg_args) > 1:
                username = msg_args[0]
                rest = ' '.join(msg_args[1:])
                tyggbot.whisper(username, rest)

    def top3(tyggbot, source, message, event, args):
        """Prints out the top 3 chatters"""
        users = []
        for user in tyggbot.users.db_session.query(User).order_by(desc(User.num_lines))[:3]:
            users.append('{user.username_raw} ({user.num_lines})'.format(user=user))

        tyggbot.say('Top 3: {0}'.format(', '.join(users)))

    def ban(tyggbot, source, message, event, args):
        if message:
            username = message.split(' ')[0]
            log.debug('banning {0}'.format(username))
            tyggbot.ban(username)

    def paid_timeout(tyggbot, source, message, event, args):
        if 'time' in args:
            _time = int(args['time'])
        else:
            _time = 600

        if message:
            username = message.split(' ')[0]
            if len(username) < 2:
                return False

            tyggbot.whisper(source.username, 'You just used {0} points to time out {1} for {2} seconds.'.format(args['command'].cost, username, _time))
            tyggbot.whisper(username, '{0} just timed you out for {1} seconds. /w {2} !$unbanme to unban yourself for points forsenMoney'.format(source.username, _time, tyggbot.nickname))
            tyggbot.timeout(username, _time)
            return True

        return False

    def set_game(tyggbot, source, message, event, args):
        if message:
            tyggbot.say('{0} updated the game to "{1}"'.format(source.username_raw, message))
            tyggbot.twitchapi.set_game(tyggbot.streamer, message)

    def ban_source(tyggbot, source, message, event, args):
        if 'filter' in args and 'notify' in args:
            if args['notify'] == 1:
                tyggbot.whisper(source.username, 'You have been permanently banned because your message matched our "{0}"-filter.'.format(args['filter'].name))

        log.debug('banning {0}'.format(source.username))
        tyggbot.ban(source.username)

    def timeout_source(tyggbot, source, message, event, args):
        if 'time' in args:
            _time = int(args['time'])
        else:
            _time = 600

        if 'filter' in args and 'notify' in args:
            if args['notify'] == 1:
                tyggbot.whisper(source.username, 'You have been timed out for {0} seconds because your message matched our "{1}"-filter.'.format(_time, args['filter'].name))

        log.debug(args)

        log.debug('timeouting {0}'.format(source.username))
        tyggbot.timeout(source.username, _time)

    def single_timeout_source(tyggbot, source, message, event, args):
        if 'time' in args:
            _time = int(args['time'])
        else:
            _time = 600

        log.debug('SINGLE timeouting {0}'.format(source.username))
        tyggbot._timeout(source.username, _time)

    def set_deck(tyggbot, source, message, event, args):
        """Dispatch method for setting the current deck.
        The command takes a link as its argument.
        If the link is an already-added deck, the deck should be set as the current deck
        and its last use date should be set to now.
        Usage: !setdeck imgur.com/abcdefgh"""

        if message:
            deck, new_deck = tyggbot.decks.set_current_deck(message)
            if new_deck is True:
                tyggbot.whisper(source.username, 'This deck is a new deck. Its ID is {deck.id}'.format(deck=deck))
            else:
                tyggbot.whisper(source.username, 'Updated an already-existing deck. Its ID is {deck.id}'.format(deck=deck))
                tyggbot.decks.commit()

            tyggbot.say('Successfully updated the latest deck.')
            return True

        return False

    def update_deck(tyggbot, source, message, event, args):
        """Dispatch method for updating a deck.
        By default this will update things for the current deck, but you can update
        any deck assuming you know its ID.
        Usage: !updatedeck --name Midrange Secret --class paladin
        """

        if message:
            options, response = tyggbot.decks.parse_update_arguments(message)
            if options is False:
                tyggbot.whisper(source.username, 'Invalid update deck command')
                return False

            if 'id' in options:
                deck = tyggbot.decks.find(id=options['id'])
                # We remove id from options here so we can tell the user what
                # they have updated.
                del options['id']
            else:
                deck = tyggbot.decks.current_deck

            if deck is None:
                tyggbot.whisper(source.username, 'No valid deck to update.')
                return False

            if len(options) == 0:
                tyggbot.whisper(source.username, 'You have given me nothing to update with the deck!')
                return False

            deck.set(**options)
            tyggbot.decks.commit()
            tyggbot.whisper(source.username, 'Updated deck with ID {deck.id}. Updated {list}'.format(deck=deck, list=', '.join([key for key in options])))

            return True
        else:
            tyggbot.whisper(source.username, 'Usage example: !updatedeck --name Midrange Secret --class paladin')
            return False

    def remove_deck(tyggbot, source, message, event, args):
        """Dispatch method for removing a deck.
        Usage: !removedeck imgur.com/abcdef
        OR
        !removedeck 123
        """

        if message:
            id = None
            try:
                id = int(message)
            except Exception:
                pass

            deck = tyggbot.decks.find(id=id, link=message)

            if deck is None:
                tyggbot.whisper(source.username, 'No deck matching your parameters found.')
                return False

            try:
                tyggbot.decks.remove_deck(deck)
                tyggbot.whisper(source.username, 'Successfully removed the deck.')
            except:
                log.exception('An exception occured while attempting to remove the deck')
                tyggbot.whisper(source.username, 'An error occured while removing your deck.')
                return False
            return True
        else:
            tyggbot.whisper(source.username, 'Usage example: !removedeck http://imgur.com/abc')
            return False

    def welcome_sub(tyggbot, source, message, event, args):
        match = args['match']

        tyggbot.kvi['active_subs'].inc()

        phrase_data = {
                'username': match.group(1)
                }

        tyggbot.say(tyggbot.phrases['new_sub'].format(**phrase_data))
        tyggbot.users[phrase_data['username']].subscriber = True

        payload = {'username': phrase_data['username']}
        tyggbot.websocket_manager.emit('new_sub', payload)

    def resub(tyggbot, source, message, event, args):
        match = args['match']

        phrase_data = {
                'username': match.group(1),
                'num_months': match.group(2)
                }

        tyggbot.say(tyggbot.phrases['resub'].format(**phrase_data))
        tyggbot.users[phrase_data['username']].subscriber = True

        payload = {'username': phrase_data['username'], 'num_months': phrase_data['num_months']}
        tyggbot.websocket_manager.emit('resub', payload)

    def sync_to(tyggbot, source, message, event, args):
        log.debug('Calling sync_to from chat command...')
        tyggbot.sync_to()

    def ignore(tyggbot, source, message, event, args):
        if message:
            tmp_username = message.split(' ')[0].strip().lower()
            user = tyggbot.users.find(tmp_username)

            if not user:
                tyggbot.whisper(source.username, 'No user with that name found.')
                return False

            if user.ignored:
                tyggbot.whisper(source.username, 'User is already ignored.')
                return False

            user.ignored = True
            user.needs_sync = True
            message = message.lower()
            tyggbot.whisper(source.username, 'Now ignoring {0}'.format(user.username))

    def unignore(tyggbot, source, message, event, args):
        if message:
            tmp_username = message.split(' ')[0].strip().lower()
            user = tyggbot.users.find(tmp_username)

            if not user:
                tyggbot.whisper(source.username, 'No user with that name found.')
                return False

            if user.ignored is False:
                tyggbot.whisper(source.username, 'User is not ignored.')
                return False

            user.ignored = False
            user.needs_sync = True
            message = message.lower()
            tyggbot.whisper(source.username, 'No longer ignoring {0}'.format(user.username))

    def permaban(tyggbot, source, message, event, args):
        if message:
            tmp_username = message.split(' ')[0].strip().lower()
            user = tyggbot.users.find(tmp_username)

            if not user:
                tyggbot.whisper(source.username, 'No user with that name found.')
                return False

            if user.banned:
                tyggbot.whisper(source.username, 'User is already permabanned.')
                return False

            user.banned = True
            user.needs_sync = True
            message = message.lower()
            tyggbot.whisper(source.username, '{0} has now been permabanned.'.format(user.username))

    def unpermaban(tyggbot, source, message, event, args):
        if message:
            tmp_username = message.split(' ')[0].strip().lower()
            user = tyggbot.users.find(tmp_username)

            if not user:
                tyggbot.whisper(source.username, 'No user with that name found.')
                return False

            if user.banned is False:
                tyggbot.whisper(source.username, 'User is not permabanned.')
                return False

            user.banned = False
            user.needs_sync = True
            message = message.lower()
            tyggbot.whisper(source.username, '{0} is no longer permabanned'.format(user.username))

    def tweet(tyggbot, source, message, event, args):
        if message and len(message) > 1 and len(message) < 140 and tyggbot.twitter:
            try:
                log.info('sending tweet: {0}'.format(message))
                tyggbot.twitter.update_status(status=message)
            except Exception as e:
                log.error('Caught an exception: {0}'.format(e))

    def eval(tyggbot, source, message, event, args):
        if tyggbot.dev and message and len(message) > 0:
            try:
                exec(message)
            except:
                log.exception('Exception caught while trying to evaluate code: "{0}"'.format(message))
        else:
            log.error('Eval cannot be used like that.')

    def check_sub(tyggbot, source, message, event, args):
        if message:
            username = message.split(' ')[0].strip().lower()
            user = tyggbot.users.find(username)
        else:
            user = source

        if user:
            if user.subscriber:
                tyggbot.say('{0} is a subscriber PogChamp'.format(user.username))
            else:
                tyggbot.say('{0} is not a subscriber FeelsBadMan'.format(user.username))
        else:
            tyggbot.say('{0} was not found in the user database'.format(username))

    def last_seen(tyggbot, source, message, event, args):
        if message:
            username = message.split(' ')[0].strip().lower()

            user = tyggbot.users.find(username)
            if user:
                tyggbot.say('{0}, {1} was last seen {2}, last active {3}'.format(source.username_raw, user.username, user.last_seen, user.last_active))
            else:
                tyggbot.say('{0}, No user with that name found.'.format(source.username_raw))

    def points(tyggbot, source, message, event, args):
        if message:
            username = message.split(' ')[0].strip().lower()
            user = tyggbot.users.find(username)
        else:
            user = source

        if user:
            if user == source:
                tyggbot.say('{0}, you have {1} points.'.format(source.username, user.points))
            else:
                tyggbot.say('{0}, {1} has {2} points.'.format(source.username, user.username, user.points))
        else:
            return False

    def remindme(tyggbot, source, message, event, args):
        if not message:
            return False

        parts = message.split(' ')
        if len(parts) < 2:
            # Not enough arguments
            return False

        delay = int(parts[0])
        extra_message = '{0} {1}'.format(source.username, ' '.join(parts[1:]).strip())

        tyggbot.execute_delayed(delay, tyggbot.say, (extra_message, ))

    def ord(tyggbot, source, message, event, args):
        if not message:
            return False

        try:
            ord_code = ord(message[0])
            tyggbot.say(str(ord_code))
        except:
            return False

    def unban_source(tyggbot, source, message, event, args):
        """Unban the user who ran the command."""
        tyggbot.privmsg('.unban {0}'.format(source.username))

    def untimeout_source(tyggbot, source, message, event, args):
        """Untimeout the user who ran the command.
        This is like unban except it will only remove timeouts, not permanent bans."""
        tyggbot.privmsg('.timeout {0} 1'.format(source.username))

    def twitter_follow(tyggbot, source, message, event, args):
        if message:
            username = message.split(' ')[0].strip().lower()
            tyggbot.twitter_manager.follow_user(username)

    def twitter_unfollow(tyggbot, source, message, event, args):
        if message:
            username = message.split(' ')[0].strip().lower()
            tyggbot.twitter_manager.unfollow_user(username)

    def reload(tyggbot, source, message, event, args):
        if message and message in tyggbot.reloadable:
            tyggbot.reloadable[message].reload()
        else:
            tyggbot.reload_all()

    def commit(tyggbot, source, message, event, args):
        if message and message in tyggbot.commitable:
            tyggbot.commitable[message].commit()
        else:
            tyggbot.commit_all()
