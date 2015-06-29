import math
import re
import json
import pymysql
import logging

from tbutil import time_limit, TimeoutException

log = logging.getLogger('tyggbot')

class Dispatch:
    """
    Methods in this class accessible from commands
    """

    def nl(tyggbot, source, message, event, args):
        if message:
            username = message.split(' ')[0].strip().lower()
        else:
            username = source.username

        num_lines = tyggbot.users[username].num_lines

        if num_lines > 0:
            tyggbot.say('{0} has typed {1} messages in this channel!'.format(username, num_lines))
        else:
            tyggbot.say('{0} hasn\'t typed anything in this channel... BibleThump'.format(username))

    def query(tyggbot, source, message, event, args):
        if Dispatch.wolfram is None:
            return False

        try:
            tyggbot.log.debug('Querying wolfram "{0}"'.format(message))
            res = Dispatch.wolfram.query(message)

            x = 0
            for pod in res.pods:
                if x == 1:
                    res = '{0}'.format(' '.join(pod.text.splitlines()).strip())
                    tyggbot.log.debug('Answering with {0}'.format(res))
                    tyggbot.say(res)
                    break

                x = x + 1
        except Exception as e:
            tyggbot.log.error('caught exception: {0}'.format(e))

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
                res = 'timed out DansGame';
                tyggbot.log.error('Timeout exception: {0}'.format(e))
            except Exception as e:
                tyggbot.log.error('Uncaught exception: {0}'.format(e))
                return

            tyggbot.say(res)

    def multi(tyggbot, source, message, event, args):
        if message:
            streams = message.strip().split(' ')
            if len(streams) == 1:
                streams.insert(0, tyggbot.target[1:])

            url = 'http://multitwitch.tv/'+'/'.join(streams)

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
        if message and len(message) > 0:
            # Step 1: Check if there's already a filter for this banphrase
            for filter in tyggbot.filters:
                if filter.type == 'banphrase':
                    if filter.filter == message:
                        tyggbot.whisper(source.username, 'That banphrase is already active (id {0})'.format(filter.id))
                        return False

            tyggbot.sqlconn.ping()
            cursor = tyggbot.sqlconn.cursor()

            action = json.dumps({'type':'func', 'cb':'timeout_source'})
            extra_args = json.dumps({'time': 300, 'notify':1})

            cursor.execute('INSERT INTO `tb_filters` (`name`, `type`, `action`, `extra_args`, `filter`) VALUES (%s, %s, %s, %s, %s)',
                    ('Banphrase', 'banphrase', action, extra_args, message))

            tyggbot.whisper(source.username, 'Successfully added your banphrase (id {0})'.format(cursor.lastrowid))

            tyggbot.sync_to()
            tyggbot._load_filters()

    def add_win(tyggbot, source, message, event, args):
        tyggbot.kvi.inc('br_wins')
        tyggbot.me('{0} added a BR win!'.format(source.username))
        tyggbot.log.debug('{0} added a BR win!'.format(source.username))

    # !add command ALIAS RESPONSE
    def add_command(tyggbot, source, message, event, args):
        if message and len(message) > 0:
            # Split up the message into multiple arguments
            # Usage example:
            # !add command ping Pong!
            # This would add the command !ping, with the response being Pong!

            # Make sure we got both an alias and a response
            message_parts = message.split(' ')
            if len(message_parts) < 2:
                tyggbot.whisper(source.username, 'Usage: !add command ALIAS RESPONSE')
                return False

            aliases = message_parts[0].lower().split('|')
            response = ' '.join(message_parts[1:])
            update_id = False

            # Check if there's already a command with these aliases
            for alias in aliases:
                if alias in tyggbot.commands:
                    if not tyggbot.commands[alias].action.type == 'say':
                        tyggbot.whisper(source.username, 'The alias {0} is already in use, and cannot be replaced.'.format(alias))
                        return False
                    else:
                        update_id = tyggbot.commands[alias].id

            data = {
                    'level': 100,
                    'command': '|'.join(aliases),
                    'action': json.dumps({'type': 'say', 'message': response.strip()}),
                    'description': 'Added by {0}'.format(source.username),
                    'delay_all': 10,
                    'delay_user': 30,
                    }

            tyggbot.sqlconn.ping()
            cursor = tyggbot.sqlconn.cursor()

            if update_id == False:
                query = 'INSERT INTO `tb_commands` (`level`, `command`, `action`, `description`, `delay_all`, `delay_user`) VALUES (' +', '.join(['%s']*len(data)) + ')'
                cursor.execute(query, (data['level'], data['command'], data['action'], data['description'], data['delay_all'], data['delay_user']))
                tyggbot.whisper(source.username, 'Successfully added your command (id {0})'.format(cursor.lastrowid))
            else:
                query = 'UPDATE `tb_commands` SET `action`=%s WHERE `id`=%s'
                cursor.execute(query, (data['action'], update_id))
                tyggbot.whisper(source.username, 'Updated an already existing command! (id {0})'.format(update_id))


            tyggbot.sync_to()
            tyggbot._load_commands()

    def remove_banphrase(tyggbot, source, message, event, args):
        if message and len(message) > 0:
            banphrase_id = int(message)

            tyggbot.sqlconn.ping()
            cursor = tyggbot.sqlconn.cursor()

            cursor.execute('DELETE FROM `tb_filters` WHERE `type`=%s AND `id`=%s',
                    ('banphrase', banphrase_id))

            if cursor.rowcount >= 1:
                tyggbot.whisper(source.username, 'Successfully removed banphrase with id {0}'.format(banphrase_id))
                tyggbot.log.debug('{0}, successfully removed banphrase with id {1}'.format(source.username, banphrase_id))
                tyggbot.sync_to()
                tyggbot._load_filters()
            else:
                tyggbot.whisper(source.username, 'No banphrase with id {0} found'.format(banphrase_id))
        else:
            tyggbot.whisper(source.username, 'Usage: !remove banphrase (BANPHRASE_ID)')

    def remove_win(tyggbot, source, message, event, args):
        tyggbot.kvi.dec('br_wins')
        tyggbot.me('{0} removed a BR win!'.format(source.username))
        tyggbot.log.debug('{0} removed a BR win!'.format(source.username))

    def remove_command(tyggbot, source, message, event, args):
        if message and len(message) > 0:
            try:
                id = int(message)
            except Exception as e:
                id = -1

            if id == -1:
                potential_cmd = ''.join(message.split(' ')[:1]).lower()
                if potential_cmd in tyggbot.commands:
                    command = tyggbot.commands[potential_cmd]
                    if not command.action.type == 'say':
                        tyggbot.whisper(source.username, 'That command is not a normal command, it cannot be removed by you.')
                        return False

                    id = command.id
                else:
                    tyggbot.whisper(source.username, 'No command with alias {1} found'.format(source.username, potential_cmd))
                    return False
            else:
                for key, command in tyggbot.commands.items():
                    if command.id == id:
                        if command.action.type is not 'say':
                            tyggbot.whisper(source.username, 'That command is not a normal command, it cannot be removed by you.')
                            return False

            tyggbot.sqlconn.ping()
            cursor = tyggbot.sqlconn.cursor()

            cursor.execute('DELETE FROM `tb_commands` WHERE `id`=%s', (id))

            if cursor.rowcount >= 1:
                tyggbot.whisper(source.username, 'Successfully removed command with id {0}'.format(id))
                tyggbot.sync_to()
                tyggbot._load_commands()
            else:
                tyggbot.whisper(source.username, 'No command with id {1} found'.format(source.username, id))
        else:
            tyggbot.whisper(source.username, 'Usage: !remove command (COMMAND_ID|COMMAND_ALIAS)')

    def debug_command(tyggbot, source, message, event, args):
        if message and len(message) > 0:
            try:
                id = int(message)
            except Exception as e:
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

            data = {
                    'id': command.id,
                    'level': command.level,
                    'type': command.action.type,
                    }

            if command.action.type == 'say':
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

            data = {
                    'id': user.id,
                    'level': user.level,
                    'num_lines': user.num_lines,
                    }

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
        tyggbot.sync_to()
        cursor = tyggbot.sqlconn.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT `username`, `num_lines` FROM `tb_user` ORDER BY `num_lines` DESC LIMIT 3')
        users = []
        for messager in cursor:
            users.append('{0} ({1})'.format(messager['username'], messager['num_lines']))

        tyggbot.say('Top 3: {0}'.format(', '.join(users)))

    def ban(tyggbot, source, message, event, args):
        if message:
            username = message.split(' ')[0]
            tyggbot.log.debug('banning {0}'.format(username))
            tyggbot.ban(username)

    def ban_source(tyggbot, source, message, event, args):
        if 'filter' in args and 'notify' in args:
            if args['notify'] == 1:
                tyggbot.whisper(source.username, 'You have been permanently banned because your message matched our "{0}"-filter.'.format(args['filter'].name))

        tyggbot.log.debug('banning {0}'.format(source.username))
        tyggbot.ban(source.username)

    def timeout_source(tyggbot, source, message, event, args):
        if 'time' in args:
            _time = int(args['time'])
        else:
            _time = 600

        if 'filter' in args and 'notify' in args:
            if args['notify'] == 1:
                tyggbot.whisper(source.username, 'You have been timed out for {0} seconds because your message matched our "{1}"-filter.'.format(_time, args['filter'].name))

        tyggbot.log.debug(args)

        tyggbot.log.debug('timeouting {0}'.format(source.username))
        tyggbot.timeout(source.username, _time)

    def single_timeout_source(tyggbot, source, message, event, args):
        if 'time' in args:
            _time = int(args['time'])
        else:
            _time = 600

        tyggbot.log.debug('SINGLE timeouting {0}'.format(source.username))
        tyggbot._timeout(source.username, _time)

    def welcome_sub(tyggbot, source, message, event, args):
        match = args['match']

        tyggbot.kvi.inc('active_subs')

        tyggbot.say('Welcome to Asgard {0}! aiaKiss'.format(match.group(1)))

    def resub(tyggbot, source, message, event, args):
        match = args['match']

        tyggbot.say('Welcome back to Asgard {0}! {1} months in a row! PogChamp'.format(match.group(1), match.group(2)))

    def sync_to(tyggbot, source, message, event, args):
        log.debug('Calling sync_to from chat command...')
        tyggbot.sync_to()

    def ignore(tyggbot, source, message, event, args):
        if message and len(message) > 1:
            message = message.lower()
            if message in tyggbot.ignores:
                tyggbot.say('Already ignoring {0}'.format(message))
            else:
                tyggbot.ignores.append(message)
                tyggbot.say('Now ignoring {0}'.format(message))
                cursor = tyggbot.get_cursor()
                cursor.execute('INSERT INTO `tb_ignores` (username) VALUES (%s)', (message))

    def unignore(tyggbot, source, message, event, args):
        if message and len(message) > 1:
            message = message.lower()
            if message in tyggbot.ignores:
                tyggbot.ignores.remove(message)
                cursor = tyggbot.get_cursor()
                cursor.execute('DELETE FROM `tb_ignores` WHERE username=%s', (message))
                tyggbot.say('No longer ignoring {0}'.format(message))
            else:
                tyggbot.say('I\'m not ignoring {0} DansGame'.format(message))
