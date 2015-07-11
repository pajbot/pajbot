import json, re, logging, time

log = logging.getLogger('tyggbot')

try:
    from userdispatch import UserDispatch
    Dispatch = UserDispatch
    log.info('Using UserDispatch')
except:
    log.exception('No user dispatch available')
    from dispatch import Dispatch


def parse_action(raw_data=None, data=None):
    from tbactions import FuncAction, RawFuncAction, SayAction, MeAction, MultiAction
    if not data: data = json.loads(raw_data)

    if data['type'] == 'say':
        action = SayAction(data['message'])
    elif data['type'] == 'me':
        action = MeAction(data['message'])
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
    def __init__(self, do_sync=True):
        self.id = -1
        self.extra_args = {}
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

    @classmethod
    def from_json(cls, json):
        cmd = cls()
        if 'level' in json: cmd.level = json['level']
        cmd.action = parse_action(data=json['action'])
        return cmd

    @classmethod
    def admin_command(cls, action, type='raw_func', level=1000):
        from tbactions import RawFuncAction, FuncAction
        cmd = cls(False)
        cmd.level = level
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
        self.enabled = data['enabled']
        self.num_uses = data['num_uses']
        if data['extra_args']:
            try:
                self.extra_args = json.loads(data['extra_args'])
            except Exception as e:
                log.error('Exception caught while loading Filter extra arguments ({0}): {1}'.format(data['extra_args'], e))

    def load_args(self, level, action):
        self.level = level
        self.action = action

    def is_enabled(self):
        return self.enabled == 1 and not self.action is None

    def sync(self, cursor):
        if self.do_sync:
            cursor.execute('UPDATE `tb_commands` SET `num_uses`=%s WHERE `id`=%s', (self.num_uses, self.id))
            self.synced = True

    # (cur_time - self.last_run) = time since last run
    def run(self, tyggbot, source, message, event={}, args={}):
        cur_time = time.time()
        if cur_time - self.last_run > self.delay_all or source.level >= 500:
            if not source.username in self.last_run_by_user or cur_time - self.last_run_by_user[source.username] > self.delay_user or source.level >= 500:
                log.info('Running action from Command')
                args.update(self.extra_args)
                ret = self.action.run(tyggbot, source, message, event, args)
                self.num_uses += 1
                self.synced = False
                if ret is not False:
                    self.last_run = cur_time
                    self.last_run_by_user[source.username] = cur_time
            else:
                log.debug('{1} ran command {0:.2f} seconds ago, waiting...'.format(cur_time - self.last_run_by_user[source.username], source.username))
        else:
            log.debug('Command was run {0:.2f} seconds ago, waiting...'.format(cur_time - self.last_run))

class Filter:
    def __init__(self, data):
        self.id = data['id']
        self.name = data['name']
        self.action = parse_action(data['action'])
        self.filter = data['filter']
        self.type = data['type']
        self.regex = re.compile(data['filter'].lower())
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

    def is_enabled(self):
        return self.enabled == 1 and not self.action is None

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
