import json
import re
import logging
import time

log = logging.getLogger('tyggbot')

try:
    from userdispatch import UserDispatch
    Dispatch = UserDispatch
    log.info('Using UserDispatch')
except:
    log.exception('No user dispatch available')
    from dispatch import Dispatch


def parse_action(raw_data=None, data=None):
    from tbactions import FuncAction, SayAction, MeAction, MultiAction, WhisperAction
    if not data:
        data = json.loads(raw_data)

    if data['type'] == 'say':
        action = SayAction(data['message'])
    elif data['type'] == 'me':
        action = MeAction(data['message'])
    elif data['type'] == 'whisper':
        action = WhisperAction(data['message'])
    elif data['type'] == 'func':
        try:
            action = FuncAction(getattr(Dispatch, data['cb']))
        except AttributeError as e:
            log.error('AttributeError caught when parsing action: {0}'.format(e))
            return None
    elif data['type'] == 'multi':
        action = MultiAction(data['args'], data['default'])
    else:
        raise Exception('Unknown action type: {0}'.format(data['type']))

    return action


class Command:
    MIN_WHISPER_LEVEL = 420
    BYPASS_DELAY_LEVEL = 2000
    BYPASS_SUB_ONLY_LEVEL = 500

    def __init__(self, do_sync=True):
        self.id = -1
        self.extra_args = {'command': self}
        self.synced = True
        self.last_run = 0
        self.last_run_by_user = {}
        self.delay_all = 0
        self.delay_user = 0
        self.num_uses = 0
        self.level = 100
        self.enabled = 1
        self.do_sync = do_sync
        self.type = '?'
        self.cost = 0
        self.can_execute_with_whisper = False
        self.sub_only = False

    @classmethod
    def from_json(cls, json):
        cmd = cls()
        if 'level' in json:
            cmd.level = json['level']
        cmd.action = parse_action(data=json['action'])
        return cmd

    @classmethod
    def dispatch_command(cls, cb, level=1000):
        cmd = cls()
        cmd.load_from_db({
            'id': -1,
            'level': level,
            'action': '{"type": "func", "cb":"' + cb + '"}',
            'do_sync': False,
            'delay_all': 0,
            'delay_user': 1,
            'extra_args': None,
            })
        return cmd

    @classmethod
    def admin_command(cls, action, type='raw_func', level=1000):
        from tbactions import RawFuncAction, FuncAction
        cmd = cls(False)
        cmd.level = level
        cmd.can_execute_with_whisper = True
        if type == 'raw_func':
            cmd.action = RawFuncAction(action)
        elif type == 'func':
            cmd.action = FuncAction(action)
        else:
            log.error('Unknown admin command type: {0}'.format(type))
            cmd.action = False
        return cmd

    def load_from_db(self, data):
        self.id = data['id']
        self.level = data['level']
        self.action = parse_action(data['action'])
        self.delay_all = data['delay_all']
        self.delay_user = data['delay_user']
        try:
            self.enabled = data['enabled']
        except:
            self.enabled = True

        try:
            self.num_uses = data['num_uses']
        except:
            self.num_uses = 0

        try:
            self.cost = data['cost']
        except:
            self.cost = 0

        try:
            self.can_execute_with_whisper = int(data['can_execute_with_whisper']) == 1
        except:
            self.can_execute_with_whisper = False

        try:
            self.sub_only = int(data['sub_only']) == 1
        except:
            self.sub_only = False

        if data['extra_args']:
            try:
                self.extra_args.update(json.loads(data['extra_args']))
            except Exception as e:
                log.error('Exception caught while loading Filter extra arguments ({0}): {1}'.format(data['extra_args'], e))

    def load_args(self, level, action):
        self.level = level
        self.action = action

    def is_enabled(self):
        return self.enabled == 1 and self.action is not None

    def sync(self, cursor):
        if self.do_sync:
            cursor.execute('UPDATE `tb_commands` SET `num_uses`=%s WHERE `id`=%s', (self.num_uses, self.id))
            self.synced = True

    def run(self, tyggbot, source, message, event={}, args={}, whisper=False):
        if source.level < self.level:
            # User does not have a high enough power level to run this command
            return False

        if whisper and self.can_execute_with_whisper is False and source.level < Command.MIN_WHISPER_LEVEL:
            # This user cannot execute the command through a whisper
            return False

        if self.sub_only and source.subscriber is False and source.level < Command.BYPASS_SUB_ONLY_LEVEL:
            # User is now a sub or a moderator, and cannot use the command.
            return False

        cur_time = time.time()
        time_since_last_run = cur_time - self.last_run

        if time_since_last_run < self.delay_all and source.level < Command.BYPASS_DELAY_LEVEL:
            log.debug('Command was run {0:.2f} seconds ago, waiting...'.format(time_since_last_run))
            return False

        time_since_last_run_user = cur_time - self.last_run_by_user.get(source.username, 0)

        if time_since_last_run_user < self.delay_user and source.level < Command.BYPASS_DELAY_LEVEL:
            log.debug('{0} ran command {1:.2f} seconds ago, waiting...'.format(source.username, time_since_last_run_user))
            return False

        if self.cost > 0 and source.points < self.cost:
            # User does not have enough points to use the command
            return False

        args.update(self.extra_args)
        ret = self.action.run(tyggbot, source, message, event, args)
        if ret is not False:
            self.num_uses += 1
            self.synced = False
            if self.cost > 0:
                # Only spend points if the action did not fail
                if not source.spend(self.cost):
                    # The user does not have enough points to spend!
                    log.warning('{0} used points he does not have.'.format(source.username))
                    return False
            self.last_run = cur_time
            self.last_run_by_user[source.username] = cur_time


class Filter:
    def __init__(self, data):
        self.id = data['id']
        self.name = data['name']
        self.action = parse_action(data['action'])
        self.filter = data['filter']
        self.type = data['type']
        self.source = data['source']
        self.num_uses = data['num_uses']
        self.enabled = data['enabled']
        self.regexstr = data['filter']
        self.extra_args = {'filter': self}
        if data['extra_args']:
            try:
                self.extra_args.update(json.loads(data['extra_args']))
            except Exception as e:
                log.error('Exception caught while loading Filter extra arguments ({0}): {1}'.format(data['extra_args'], e))

        self.synced = True

        try:
            self.regex = re.compile(data['filter'].lower())
        except Exception as e:
            log.exception('Uncaught exception in filter {0}'.format(self.name))
            self.enabled = False

    def is_enabled(self):
        return self.enabled == 1 and self.action is not None

    def sync(self, cursor):
        cursor.execute('UPDATE `tb_filters` SET `num_uses`=%s WHERE `id`=%s', (self.num_uses, self.id))
        self.synced = True

    def match(self, source, message):
        if not self.source or self.source == source:
            return self.regex.match(message)

    def search(self, source, message):
        if not self.source or self.source == source.username:
            return self.regex.search(message)

        return None

    def run(self, tyggbot, source, message, event={}, args={}):
        args.update(self.extra_args)
        self.action.run(tyggbot, source, message, event, args)
        self.num_uses += 1
        self.synced = False
