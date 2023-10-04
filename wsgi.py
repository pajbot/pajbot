#!/usr/bin/env python3
import pajbot.web
from pajbot.utils import init_logging
from pajbot.web import app

init_logging("pajbot")

# TODO: Make this configurable some way - maybe through an environment variable?
pajbot.web.init("config.ini")

if __name__ == "__main__":
    app.run()
