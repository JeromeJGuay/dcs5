"""
May 2022 JeromeJGuay
This modules contains script to init the logger.
"""
import logging
import sys
import time

from dcs5 import LOG_FILES_PATH

LOG_FILE_PREFIX = "dcs5_log"


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
    file_level :
        Level of the file logging.
    write :
        If True, writes the logfile to file_path.

    Returns
    -------

    """

    formatter = BasicLoggerFormatter()
    handlers = []
    filename=None
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
        filename = LOG_FILES_PATH.joinpath(time.strftime("%y%m%dT%H%M%S", time.gmtime())).with_suffix('.log')

        file_handler = logging.FileHandler(filename)
        file_handler.setLevel(file_level.upper())
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    logging.basicConfig(level="NOTSET", handlers=handlers)

    logging.debug('Logging Started.')
    return filename


