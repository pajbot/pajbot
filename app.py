#!/usr/bin/env python3
import argparse

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

pajbot.web.init(args)

if __name__ == "__main__":
    app.run(debug=args.debug, host=args.host, port=args.port)
