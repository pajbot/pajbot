#!/usr/bin/env python3

import threading, os, sys, time, configparser, signal, argparse, logging, json

import pika
import pymysql

from kvidata import KVIData
from tyggbot import TyggBot
from daemon import Daemon

def pika_listen(channel):
    channel.start_consuming()

os.chdir(os.path.dirname(os.path.realpath(__file__)))

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

def command_consume(ch, method, properties, body):
    global tyggbot

    if not properties.headers or 'user' not in properties.headers:
        tyggbot.log.warning('no user header found')
        return False

    tyggbot.log.info("Received '{0}' from Squirrel".format(body))

    tyggbot.parse_message(body.decode('utf-8'), properties.headers['user'], force=True)

class TBDaemon(Daemon):
    def run(self):
        global tyggbot
        global args

        tyggbot = TyggBot(config, args)

        tyggbot.connect()

        connection = pika.BlockingConnection(pika.ConnectionParameters(
                host='localhost'))
        channel = connection.channel()

        channel_arguments = {
                'x-expires': 750,
                }

        queue_name = '{0}_tb_commands'.format(tyggbot.nickname)

        tyggbot.log.info('Listening to queue \'{0}\''.format(queue_name))

        channel.queue_declare(queue=queue_name, auto_delete=True, arguments=channel_arguments)

        channel.basic_consume(command_consume,
                              queue=queue_name,
                              no_ack=True)

        pika_thread = threading.Thread(target=pika_listen, args={channel})
        pika_thread.daemon = True

        def on_sigterm(signal, frame):
            tyggbot.quit()
            sys.exit(0)

        signal.signal(signal.SIGTERM, on_sigterm)

        try:
            pika_thread.start()
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
