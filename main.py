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

from tyggbot.tyggbot import TyggBot


def run(args):
    from tyggbot.tbutil import load_config
    config = load_config(args.config)

    if 'main' not in config:
        log.error('Missing section [main] in config')
        sys.exit(1)

    if 'sql' in config:
        log.error('The [sql] section in config is no longer used. See config.example.ini for the new format under [main].')
        sys.exit(1)

    if 'db' not in config['main']:
        log.error('Missing required db config in the [main] section.')
        sys.exit(1)

    tyggbot = TyggBot(config, args)

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
    from tyggbot.tbutil import init_logging

    sys.excepthook = handle_exceptions

    args = TyggBot.parse_args()

    init_logging('tyggbot')
    run(args)
