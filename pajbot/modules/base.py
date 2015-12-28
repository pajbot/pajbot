class BaseModule:
    """ This class will include all the basics that a module needs
    to be operable.
    """

    ID = __name__.split('.')[-1]
    NAME = 'Base Module'
    DESCRIPTION = 'This is the description for the base module. ' + \
            'It\'s what will be shown on the website where you can enable ' + \
            'and disable modules.'

    def __init__(self):
        """ Initialize any dictionaries the module might or might not use. """
        self.commands = {}
        self.settings = {}

    def load(self, **options):
        """ This method will load everything from the module into
        their proper dictionaries, which we can then use later. """

        self.load_commands(**options)

        if 'settings' in options:
            try:
                self.settings = json.loads(options['settings'])
            except:
                pass

        return self

    def load_commands(self, **options):
        pass
