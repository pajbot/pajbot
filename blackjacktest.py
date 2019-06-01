#!/usr/bin/env python3

import logging

from pajbot.modules.blackjack import BlackjackGame

logging.basicConfig(level=logging.DEBUG)


print("hello")

game = BlackjackGame(None, None, 500)

game.print_state()
