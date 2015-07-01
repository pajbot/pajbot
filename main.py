#!/usr/bin/env python3

import threading, os, sys, time, signal, argparse, logging, json

try:
    basestring
except NameError:
    basestring = str

os.chdir(os.path.dirname(os.path.realpath(__file__)))

log = logging.getLogger('tyggbot')

import pymysql

from kvidata import KVIData
from tyggbot import TyggBot
from daemon import Daemon

def load_config(path):
    import configparser
    config = configparser.ConfigParser()

    configfile = os.path.dirname(os.path.realpath(__file__)) + '/' + path
    res = config.read(configfile)

    if len(res) == 0:
        log.error('{0} missing. Check out install/config.example.ini'.format(path))
        sys.exit(0)

    if not 'main' in config:
        log.error('Missing section [main] in {0}'.format(path))
        sys.exit(0)

    if not 'sql' in config:
        log.error('Missing section [sql] in {0}'.format(path))
        sys.exit(0)

    return config

class TBDaemon(Daemon):
    def __init__(self, pidfile, args):
        self.pidfile = pidfile
        self.args = args

    def run(self):
        tyggbot = TyggBot(load_config(self.args.config), self.args)

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

    pidfile = os.path.dirname(os.path.realpath(__file__)) + '/' + args.pidfile

    init_logging(args.logfile, 'tyggbot')
    daemon = TBDaemon(pidfile, args)

    if args.action == 'start':
        daemon.start()
    elif args.action == 'stop':
        daemon.stop()
    elif args.action == 'restart':
        daemon.restart()
    else:
        daemon.run()
