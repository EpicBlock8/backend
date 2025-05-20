import logging
import re
import sys
from datetime import datetime
from pathlib import Path

from colorama import Fore, Style, init

from app.shared import Config, load_config

config: Config = load_config()


class Logger:
    def __init__(self, name, log_file=config.paths.logs, level=logging.INFO):
        Path(log_file).mkdir(parents=True, exist_ok=True)
        # Initialize colorama
        init()

        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        format_string_console = (
            f"{Style.BRIGHT}%(levelname)-10s "
            + f"{Style.DIM}%(name)-20s "
            + "%(module)s.%(funcName)-30s "
            + f"{Style.RESET_ALL}%(message)s"
        )
        format_string_file = re.sub(
            r"\x1b\[[0-9;]*m", "", "%(asctime)s - " + format_string_console
        )

        # Create formatter
        file_formatter = logging.Formatter(format_string_file)

        # Create file handler
        file_handler = logging.FileHandler(
            log_file + f"/{datetime.now().strftime('%Y-%m-%d')}.log"
        )
        file_handler.setFormatter(file_formatter)

        # Create colored console handler
        class ColorFormatter(logging.Formatter):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.color_map = {
                    logging.DEBUG: Fore.CYAN,
                    logging.INFO: Fore.GREEN,
                    logging.WARNING: Fore.YELLOW,
                    logging.ERROR: Fore.RED,
                    logging.CRITICAL: Fore.MAGENTA,
                }

            def format(self, record):
                color = self.color_map.get(record.levelno, Fore.WHITE)
                message = super().format(record)
                return f"{color}{message}{Style.RESET_ALL}"

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColorFormatter(format_string_console))

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def get_logger(self):
        return self.logger
