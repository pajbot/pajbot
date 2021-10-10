import logging
import sys

from colorama import Fore, Style


def init_logging(app: str = "pajbot") -> logging.Logger:
    class LogFilter(logging.Filter):
        def __init__(self, level: int) -> None:
            super().__init__()
            self.level = level

        def filter(self, record: logging.LogRecord) -> bool:
            return record.levelno < self.level

    colors = {
        "WARNING": Fore.YELLOW,
        "INFO": Fore.WHITE,
        "DEBUG": Fore.BLUE,
        "CRITICAL": Fore.YELLOW,
        "ERROR": Fore.RED,
    }

    class ColoredFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            levelname = record.levelname
            if levelname in colors:
                levelname_color = Style.BRIGHT + colors[levelname] + levelname + Style.RESET_ALL
                record.levelname = levelname_color
            return logging.Formatter.format(self, record)

    # Uncomment the line below if you want full debug messages from everything!
    # This includes all debug messages from the IRC libraries, which can be useful for debugging.
    # logging.basicConfig(level=logging.DEBUG - 2)

    logger = logging.getLogger(app)
    logger.setLevel(logging.DEBUG)

    colored_formatter = ColoredFormatter("[%(asctime)s] [%(levelname)-20s] %(message)s")
    log_filter = LogFilter(logging.WARNING)

    logger_stdout = logging.StreamHandler(sys.stdout)
    logger_stdout.setFormatter(colored_formatter)
    logger_stdout.addFilter(log_filter)
    logger_stdout.setLevel(logging.DEBUG)

    logger_stderr = logging.StreamHandler(sys.stderr)
    logger_stderr.setFormatter(colored_formatter)
    logger_stderr.setLevel(logging.WARNING)

    logging.getLogger().addHandler(logger_stdout)
    logging.getLogger().addHandler(logger_stderr)

    return logger
