#!/usr/bin/env python3

import os
import sys
import signal
import logging

try:
    basestring
except NameError:
    basestring = str

os.chdir(os.path.dirname(os.path.realpath(__file__)))

log = logging.getLogger('tyggbot')

from tyggbot import TyggBot


def load_config(path):
    import configparser
    config = configparser.ConfigParser()

    configfile = os.path.dirname(os.path.realpath(__file__)) + '/' + path
    res = config.read(configfile)

    if len(res) == 0:
        log.error('{0} missing. Check out install/config.example.ini'.format(path))
        sys.exit(0)

    if 'main' not in config:
        log.error('Missing section [main] in {0}'.format(path))
        sys.exit(0)

    if 'sql' not in config:
        log.error('Missing section [sql] in {0}'.format(path))
        sys.exit(0)

    return config


def run(args):
    tyggbot = TyggBot(load_config(args.config), args)

    tyggbot.connect()

    def on_sigterm(signal, frame):
        tyggbot.quit()
        sys.exit(0)

    signal.signal(signal.SIGTERM, on_sigterm)

    try:
        tyggbot.start()
    except KeyboardInterrupt:
        tyggbot.quit()
        pass


def handle_exceptions(exctype, value, tb):
    log.error('Logging an uncaught exception', exc_info=(exctype, value, tb))

if __name__ == "__main__":
    from tbutil import init_logging

    sys.excepthook = handle_exceptions

    args = TyggBot.parse_args()

    init_logging('tyggbot')
    run(args)
