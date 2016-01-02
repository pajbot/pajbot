import json
import logging

from pajbot.tbutil import find

log = logging.getLogger(__name__)

class ModuleSetting:
    """
    Available constraints:
    min_str_len
    max_str_len
    """

    def __init__(self, key, label, type, required=False,
                 placeholder='', default=None, constraints={}):
        self.key = key
        self.label = label
        self.type = type
        self.required = required
        self.placeholder = placeholder
        self.default = default
        self.constraints = constraints
        self.validators = {
                'text': self.validate_text
                }

    def validate(self, value):
        if self.type in self.validators:
            return self.validators[self.type](value)
        else:
            log.info('No validator available for type {}'.format(type))
            return True, value

    def validate_text(self, value):
        value = value.strip()
        if 'min_str_len' in self.constraints and len(value) < self.constraints['min_str_len']:
            return False, 'needs to be at least {} characters long'.format(self.constraints['min_str_len'])
        if 'max_str_len' in self.constraints and len(value) > self.constraints['max_str_len']:
            return False, 'needs to be at most {} characters long'.format(self.constraints['max_str_len'])
        return True, value

class BaseModule:
    """ This class will include all the basics that a module needs
    to be operable.
    """

    ID = __name__.split('.')[-1]
    NAME = 'Base Module'
    DESCRIPTION = 'This is the description for the base module. ' + \
            'It\'s what will be shown on the website where you can enable ' + \
            'and disable modules.'
    SETTINGS = []

    def __init__(self):
        """ Initialize any dictionaries the module might or might not use. """
        self.commands = {}
        self.settings = {}

    def load(self, **options):
        """ This method will load everything from the module into
        their proper dictionaries, which we can then use later. """

        self.load_settings(options.get('settings', {}))

        self.load_commands(**options)

        return self

    def load_settings(self, settings):
        self.settings = settings

        # Load any unset settings
        for setting in self.SETTINGS:
            if setting.key not in self.settings:
                self.settings[setting.key] = setting.default

    def load_commands(self, **options):
        pass

    def parse_settings(self, **in_settings):
        for key, value in in_settings.items():
            setting = find(lambda setting: setting.key == key, self.SETTINGS)
            if setting is None:
                return False
            print('{}: {}'.format(key, value))
            res, new_value = setting.validate(value)
            print(res)
            print(new_value)
            print(type(new_value))

    def enable(self, bot):
        pass

    def disable(self, bot):
        pass
