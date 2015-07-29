import logging

log = logging.getLogger('tyggbot')

class Setting:
    def parse(type, value):
        try:
            if type == 'int':
                return int(value)
            elif type == 'string':
                return value
            elif type == 'list':
                return value.split(',')
            elif type == 'bool':
                return int(value) == 1
            else:
                log.error('Invalid setting type: {0}'.format(type))
        except Exception as e:
            log.exception('Exception caught when loading setting')

        return None
