"""
May 2022 JeromeJGuay
This modules contains script to init the logger.
"""
import logging
import sys
import time
from pathlib import Path

from dcs5.utils import resolve_relative_path

DEFAULT_FILE_PATH = "../logs/dcs5_log"


class BasicLoggerFormatter(logging.Formatter):
    level_width = 10
    thread_width = 10

    def format(self, record):
        fmt_time = "("+self.formatTime(record, self.datefmt)+")"
        fmt_thread = f"{'{'}{record.threadName}{'}'}".ljust(self.thread_width)
        fmt_level = f"[{record.levelname}]".ljust(self.level_width)
        fmt_message = record.getMessage()
        return f"{fmt_time} - {fmt_thread} - {fmt_level} - {fmt_message}"


class UiLoggerFormatter(logging.Formatter):
    level_width = 10
    thread_width = 10

    def format(self, record):
        fmt_time = "("+self.formatTime(record, self.datefmt)+")"
        fmt_message = record.getMessage().strip("ui: ")
        return f"{fmt_time} - {fmt_message}"


class UserInterfaceFilter(logging.Filter):
    def filter(self, record):
        return record.getMessage().startswith("ui:")


def init_logging(
        stdout_level="INFO",
        ui=False,
        file_path=None,
        file_level="DEBUG",
        write=False,
):
    """

    Parameters
    ----------
    stdout_level :
        Level of the sys.output logging.
    ui :
        Show ui (user interface) log messages. (logging.Filter).
    file_path :
        path where to save the log file. Defaults to dcs5/dcs5/logs/dcs5_log_{YYYYMMDDThhmmss}.log
    file_level :
        Level of the file logging.
    write :
        If True, writes the logfile to file_path.

    Returns
    -------

    """
    file_path = resolve_relative_path(DEFAULT_FILE_PATH, __file__) or file_path

    formatter = BasicLoggerFormatter()
    handlers = []

    stdout_handler = logging.StreamHandler(sys.stdout)
    if ui is True:
        stdout_handler.setLevel("INFO")
        stdout_handler.addFilter(UserInterfaceFilter())
        stdout_handler.setFormatter(UiLoggerFormatter())
    else:
        stdout_handler.setLevel(stdout_level.upper())
        stdout_handler.setFormatter(formatter)

    handlers.append(stdout_handler)

    if write is True:
        file_handler = logging.FileHandler(format_log_path(file_path))
        file_handler.setLevel(file_level.upper())
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    logging.basicConfig(level="NOTSET", handlers=handlers)


def format_log_path(path: str) -> str:
    new_stem = Path(path).stem + "_" + time.strftime("%y%m%dT%H%M%S", time.gmtime())
    return str(Path(path).parent.joinpath(Path(new_stem)).with_suffix('.log'))
