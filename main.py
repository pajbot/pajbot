#!/usr/bin/env python3
import logging
import os
import signal
import sys

from pajbot.bot import Bot
from pajbot.utils import parse_args

try:
    basestring
except NameError:
    basestring = str

# XXX: What does this achieve exactly?
os.chdir(os.path.dirname(os.path.realpath(__file__)))

log = logging.getLogger(__name__)


def run(args):
    from pajbot.utils import load_config

    config = load_config(args.config)

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

    pajbot.connect()

    def on_sigterm(signal, frame):
        pajbot.quit_bot()
        sys.exit(0)

    signal.signal(signal.SIGTERM, on_sigterm)

    try:
        pajbot.start()
    except KeyboardInterrupt:
        pajbot.quit_bot()


def handle_exceptions(exctype, value, tb):
    log.error("Logging an uncaught exception", exc_info=(exctype, value, tb))


if __name__ == "__main__":
    from pajbot.utils import init_logging, dump_threads

    def on_sigusr1(signal, frame):
        log.info("Process was interrupted with SIGUSR1, dumping all thread stack traces")
        dump_threads()

    # dump all stack traces on SIGUSR1
    signal.signal(signal.SIGUSR1, on_sigusr1)
    sys.excepthook = handle_exceptions

    args = parse_args()

    init_logging("pajbot")
    run(args)
