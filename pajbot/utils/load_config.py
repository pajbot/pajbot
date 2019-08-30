import configparser
import os

import logging
import sys

log = logging.getLogger(__name__)


def load_config(path):
    config = configparser.ConfigParser()
    config.read_dict({"web": {"deck_tab_images": "1"}})

    res = config.read(os.path.realpath(path))

    if not res:
        log.error("%s missing. Check out the example config file.", path)
        sys.exit(0)

    return config
