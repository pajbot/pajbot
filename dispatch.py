import math
import re
import json
import pymysql

from tbutil import time_limit, TimeoutException

class Dispatch:
    """
    Methods in this class accessible from commands
    """

    def nl(tyggbot, source, message, event, args):
        if message:
            username = message.split(' ')[0].strip().lower()
        else:
            username = event.source.user.lower()

        if username in tyggbot.num_messages:
            num_lines = tyggbot.num_messages[username].value
        else:
            num_lines = 0

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
                    res = '{2}, {0} {1}'.format(expr_res, emote, event.source.user)
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

            tyggbot.say('{0}, {1}'.format(event.source.user, url))

    def ab(tyggbot, source, message, event, args):
        if message:
            message = re.sub(' +', ' ', message)

            msg_parts = message.split(' ')
            if len(msg_parts) >= 2:
                s = ''
                for c in msg_parts[1]:
                    s += msg_parts[0] + ' ' + c + ' '
                s += msg_parts[0]

                tyggbot.say('{0}, {1}'.format(source.user, s))

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

                tyggbot.say('{0}, {1}'.format(source.user, s))

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
                        tyggbot.me('{0}, that banphrase is already active (id {1})'.format(source.user, filter.id))
                        return False

            tyggbot.sqlconn.ping()
            cursor = tyggbot.sqlconn.cursor()

            action = json.dumps({'type':'func', 'cb':'timeout_source'})
            extra_args = json.dumps({'time': 300, 'notify':1})

            cursor.execute('INSERT INTO `tb_filters` (`name`, `type`, `action`, `extra_args`, `filter`) VALUES (%s, %s, %s, %s, %s)',
                    ('Banphrase', 'banphrase', action, extra_args, message))

            tyggbot.me('{0}, successfully added your banphrase (id {1})'.format(source.user, cursor.lastrowid))

            tyggbot.log.debug('{0}, successfully added your banphrase (id {1})'.format(source.user, cursor.lastrowid))

            tyggbot.sync_to()
            tyggbot._load_filters()

    def add_win(tyggbot, source, message, event, args):
        tyggbot.kvi.inc('br_wins')
        tyggbot.me('{0} added a BR win!'.format(source.user))
        tyggbot.log.debug('{0} added a BR win!'.format(source.user))

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
                tyggbot.whisper(source.user, 'Usage: !add command ALIAS RESPONSE')
                return False

            aliases = message_parts[0].lower().split('|')
            response = ' '.join(message_parts[1:])

            # Check if there's already a command with these aliases
            for alias in aliases:
                if alias in tyggbot.commands:
                    tyggbot.whisper(source.user, 'The alias {0} is already in use.'.format(alias))
                    return False

            data = {
                    'level': 100,
                    'command': '|'.join(aliases),
                    'action': json.dumps({'type': 'say', 'message': response.strip()}),
                    'description': 'Added by {0}'.format(source.user),
                    'delay_all': 10,
                    'delay_user': 30,
                    }

            tyggbot.sqlconn.ping()
            cursor = tyggbot.sqlconn.cursor()

            query = 'INSERT INTO `tb_commands` (`level`, `command`, `action`, `description`, `delay_all`, `delay_user`) VALUES (' +', '.join(['%s']*len(data)) + ')'

            cursor.execute(query, (data['level'], data['command'], data['action'], data['description'], data['delay_all'], data['delay_user']))

            tyggbot.me('{0}, successfully added your command (id {1})'.format(source.user, cursor.lastrowid))

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
                tyggbot.me('{0}, successfully removed banphrase with id {1}'.format(source.user, banphrase_id))
                tyggbot.log.debug('{0}, successfully removed banphrase with id {1}'.format(source.user, banphrase_id))
                tyggbot.sync_to()
                tyggbot._load_filters()
            else:
                tyggbot.me('{0}, no banphrase with id {1} found'.format(source.user, banphrase_id))

    def remove_win(tyggbot, source, message, event, args):
        tyggbot.kvi.dec('br_wins')
        tyggbot.me('{0} removed a BR win!'.format(source.user))
        tyggbot.log.debug('{0} removed a BR win!'.format(source.user))

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
                        tyggbot.whisper(source.user, 'That command is not a normal command, it cannot be removed by you.')
                        return False

                    id =  command.id
                else:
                    tyggbot.whisper(source.user, 'No command with alias {1} found'.format(source.user, potential_cmd))
                    return False
            else:
                for key, command in tyggbot.commands.items():
                    if command.id == id:
                        if command.action.type is not 'say':
                            tyggbot.whisper(source.user, 'That command is not a normal command, it cannot be removed by you.')
                            return False

            tyggbot.sqlconn.ping()
            cursor = tyggbot.sqlconn.cursor()

            cursor.execute('DELETE FROM `tb_commands` WHERE `id`=%s', (id))

            if cursor.rowcount >= 1:
                tyggbot.me('{0}, successfully removed command with id {1}'.format(source.user, id))
                tyggbot.sync_to()
                tyggbot._load_commands()
            else:
                tyggbot.whisper(source.user, 'No command with id {1} found'.format(source.user, id))

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
        cursor = tyggbot.sqlconn.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT `id`, `value` FROM `tb_idata` WHERE `type`=\'nl\' ORDER BY `value` DESC LIMIT 3')
        users = []
        for messager in cursor:
            users.append('{0} ({1})'.format(messager['id'], messager['value']))

        tyggbot.say('Top 3: {0}'.format(', '.join(users)))

    def ban(tyggbot, source, message, event, args):
        if message:
            username = message.split(' ')[0]
            tyggbot.log.debug('banning {0}'.format(username))
            tyggbot.ban(username)

    def ban_source(tyggbot, source, message, event, args):
        if 'filter' in args and 'notify' in args:
            if args['notify'] == 1:
                tyggbot.whisper(event.source.user, 'You have been permanently banned because your message matched our "{0}"-filter.'.format(args['filter'].name))

        username = event.source.user.lower()
        tyggbot.log.debug('banning {0}'.format(username))
        tyggbot.ban(username)

    def timeout_source(tyggbot, source, message, event, args):
        if 'time' in args:
            _time = int(args['time'])
        else:
            _time = 600

        if 'filter' in args and 'notify' in args:
            if args['notify'] == 1:
                tyggbot.whisper(event.source.user, 'You have been timed out for {0} seconds because your message matched our "{1}"-filter.'.format(_time, args['filter'].name))

        tyggbot.log.debug(args)

        username = event.source.user.lower()
        tyggbot.log.debug('timeouting {0}'.format(username))
        tyggbot.timeout(username, _time)

    def single_timeout_source(tyggbot, source, message, event, args):
        if 'time' in args:
            _time = int(args['time'])
        else:
            _time = 600

        username = event.source.user.lower()
        tyggbot.log.debug('SINGLE timeouting {0}'.format(username))
        tyggbot._timeout(username, _time)

    def welcome_sub(tyggbot, source, message, event, args):
        match = args['match']

        tyggbot.kvi.inc('active_subs')

        tyggbot.say('Welcome to Asgard {0}! aiaKiss'.format(match.group(1)))

    def resub(tyggbot, source, message, event, args):
        match = args['match']

        tyggbot.say('Welcome back to Asgard {0}! {1} months in a row! PogChamp'.format(match.group(1), match.group(2)))

    def sync_to(tyggbot, source, message, event, args):
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
