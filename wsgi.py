#!/usr/bin/env python3
import pajbot_webapp
from pajbot.utils import init_logging
from pajbot_webapp import app

init_logging("pajbot")

# TODO: Make this configurable some way - maybe through an environment variable?
pajbot_webapp.init("config.ini")

if __name__ == "__main__":
    app.run()
