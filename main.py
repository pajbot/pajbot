#!/usr/bin/env python3

import threading, os, sys, time, configparser, signal, argparse, logging, json
from tbutil import init_logging

try:
    basestring
except NameError:
    basestring = str

os.chdir(os.path.dirname(os.path.realpath(__file__)))
init_logging('all.log', 'tyggbot')

log = logging.getLogger('tyggbot')

import pymysql

from kvidata import KVIData
from tyggbot import TyggBot
from daemon import Daemon

config = configparser.ConfigParser()

res = config.read('config.ini')

if len(res) == 0:
    print('config.ini missing. Check out config.example.ini for the relevant data')
    sys.exit(0)

if not 'main' in config:
    print('Missing section [main] in config.ini')
    sys.exit(0)

if not 'sql' in config:
    print('Missing section [sql] in config.ini')
    sys.exit(0)

tyggbot = None
args = None

class TBDaemon(Daemon):
    def run(self):
        global tyggbot
        global args

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
    logging.getLogger('tyggbot').error('Logging an uncaught exception', exc_info=(exctype, value, tb))

if __name__ == "__main__":
    sys.excepthook = handle_exceptions
    pid_path = os.path.dirname(os.path.realpath(__file__)) + '/.bot.pid'

    args = TyggBot.parse_args()

    if args.action == 'start':
        TBDaemon(pid_path).start()
    elif args.action == 'stop':
        TBDaemon(pid_path).stop()
    elif args.action == 'restart':
        TBDaemon(pid_path).restart()
    else:
        TBDaemon(pid_path).run()
