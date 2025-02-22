#!/usr/bin/env python3

import asyncio
import logging
import os
import signal
import sys

from pajbot.bot import Bot
from pajbot.managers.schedule import ScheduleManager
from pajbot.utils import parse_args

import grpc
from grpc_reflection.v1alpha import reflection
from pajbot.protos import bot_pb2
from pajbot.protos import bot_pb2_grpc

try:
    basestring
except NameError:
    basestring = str

# XXX: What does this achieve exactly?
os.chdir(os.path.dirname(os.path.realpath(__file__)))

log = logging.getLogger(__name__)


async def serve(bot: Bot) -> None:
    print("XDDDDDDDDDD")
    log.info("serve start")
    server = grpc.aio.server()
    bot_pb2_grpc.add_BotServicer_to_server(bot, server)
    listen_addr = "127.0.0.1:50051"
    server.add_insecure_port(listen_addr)
    logging.info("Starting server on %s", listen_addr)

    service_names = (
        bot_pb2.DESCRIPTOR.services_by_name["Bot"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(service_names, server)

    print("serve start!")
    await server.start()
    print("serve started!")
    await server.wait_for_termination()
    print("serve waited!")


def handle_exceptions(exctype, value, tb):
    log.error("Logging an uncaught exception", exc_info=(exctype, value, tb))


async def main_coro():
    from pajbot.utils import dump_threads, init_logging

    init_logging("pajbot")

    def on_sigusr1(signal, frame):
        log.info("Process was interrupted with SIGUSR1, dumping all thread stack traces")
        dump_threads()

    # dump all stack traces on SIGUSR1
    signal.signal(signal.SIGUSR1, on_sigusr1)
    sys.excepthook = handle_exceptions

    args = parse_args()

    from pajbot.utils import load_config

    config = load_config(args.config)

    loop = asyncio.get_event_loop()

    if "main" not in config:
        log.error("Missing section [main] in config")
        sys.exit(1)

    if "sql" in config:
        log.error(
            "The [sql] section in config is no longer used. See the example config for the new format under [main]."
        )
        sys.exit(1)

    if "db" not in config["main"]:
        log.error("Missing required db config in the [main] section.")
        sys.exit(1)

    pajbot = Bot(config, args)
    await pajbot.init(config, args)

    print("connect start")
    # pajbot.connect()
    print("connect end")

    grpc_task = loop.create_task(serve(pajbot))
    socket_manager_task = loop.create_task(pajbot.socket_manager.start())

    # await grpc_task

    # aaa = pajbot.execute_every(1, lambda: print("AAAAAA"))
    # aaa.set_name("aaaaaa")
    # pajbot.execute_delayed(1.5, lambda: print("BBBBBB"))

    ScheduleManager.execute_delayed(1.6, lambda: print("CCCCCCCC"))

    # def on_sigterm(signal, frame):
    #     pajbot.quit_bot()
    #     sys.exit(0)

    # signal.signal(signal.SIGTERM, on_sigterm)

    try:
        await asyncio.gather(grpc_task, socket_manager_task)
    except asyncio.CancelledError:
        print("CANCELLED")
        try:
            pass
            # pajbot.quit_bot()
        except asyncio.CancelledError:
            print("ctrl+c pressed again, force quit")

    grpc_task.cancel()

    # aaa.cancel()

    # TODO: Do we need to cancel remaining tasks?


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    main_task = asyncio.ensure_future(main_coro())
    for sig in [signal.SIGINT, signal.SIGTERM]:
        loop.add_signal_handler(sig, main_task.cancel)
    try:
        loop.run_until_complete(main_task)
    finally:
        loop.close()
