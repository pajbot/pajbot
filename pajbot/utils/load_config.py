from typing import Any, Dict

import configparser
import logging
import os
import sys

log = logging.getLogger(__name__)


def config_to_dict(config: configparser.ConfigParser) -> Dict[str, Dict[str, Any]]:
    r: Dict[str, Any] = {}

    for section in config.sections():
        r[section] = {}
        for key, val in config.items(section):
            r[section][key] = val

    return r


def load_config(path: str) -> Dict[str, Any]:
    config = configparser.ConfigParser()
    config.read_dict({"web": {"deck_tab_images": "1"}})

    res = config.read(os.path.realpath(path))

    if not res:
        log.error("%s missing. Check out the example config file.", path)
        sys.exit(0)

    return config_to_dict(config)
