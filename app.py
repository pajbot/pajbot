#!/usr/bin/env python3
import argparse
import asyncio
import logging
import signal

import pajbot.web
from pajbot.utils import init_logging
from pajbot.web import app

init_logging("pajbot")

parser = argparse.ArgumentParser(description="start the web app")
parser.add_argument("--config", default="config.ini")
parser.add_argument("--host", default="0.0.0.0")
parser.add_argument("--port", type=int, default=2325)
parser.add_argument("--debug", dest="debug", action="store_true")
parser.add_argument("--no-debug", dest="debug", action="store_false")
parser.set_defaults(debug=False)

args = parser.parse_args()

log = logging.getLogger(__name__)


async def main_coro() -> None:
    log.info("init")
    await pajbot.web.init(args.config)
    log.info("app run")
    app.run(debug=args.debug, host=args.host, port=args.port)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    main_task = asyncio.ensure_future(main_coro())
    try:
        loop.run_until_complete(main_task)
    finally:
        loop.close()
