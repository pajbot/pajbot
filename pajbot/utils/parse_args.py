import argparse


def parse_args():
    """
    Parse command-line arguments for the bot.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", "-c", default="config.ini", help="Specify which config file to use (default: config.ini)"
    )
    parser.add_argument("--silent", action="count", help="Decides whether the bot should be silent or not")
    # TODO: Add a log level argument.

    return parser.parse_args()
