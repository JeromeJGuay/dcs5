"""
May 2022 JeromeJGuay
This modules contains script to init the logger.
"""
import logging
import sys
import time
import re
from pathlib import Path

from dcs5 import LOG_FILES_PATH

LOG_FILE_PREFIX = "dcs5_log"

RED_TEXT = "\x1b[31;20m"
YELLOW_TEXT = "\x1b[33;20m"
RESET_TEXT = "\x1b[0m"


class BasicLoggerFormatter(logging.Formatter):
    level_width = 10
    thread_width = 10
    colors = {'WARNING': YELLOW_TEXT, 'ERROR': RED_TEXT}

    def format(self, record):
        color = ''
        if record.levelname in self.colors:
            color = self.colors[record.levelname]
        fmt_time = "("+self.formatTime(record, self.datefmt)+")"
        fmt_thread = f"{'{'}{record.threadName}{'}'}".ljust(self.thread_width)
        fmt_level = f"[{record.levelname}]".ljust(self.level_width)
        fmt_message = record.getMessage()
        return f"{color}{fmt_time} - {fmt_thread} - {fmt_level} - {fmt_message}{RESET_TEXT}"


class MultilineStdHandler:
    """
    Handler for PySimpleGui Multiline.
    """
    def __init__(self, window, key):
        self.window = window
        self.key = key
        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def write(self, s):
        c = 'red' if RED_TEXT in s else 'yellow' if YELLOW_TEXT in s else None
        _s = self.ansi_escape.sub('', s)
        try:
            self.window[self.key].update(value=_s, append=True, text_color_for_value = c)
        except RuntimeError:
            pass

    def flush(self):
        return


def get_multiline_handler(window, key, level='DEBUG"'):
    window_handler = logging.StreamHandler(MultilineStdHandler(window=window, key=key))
    window_handler.setLevel(level.upper())
    window_handler.setFormatter(BasicLoggerFormatter())

    return window_handler


def clean_old_log_files(max_count=20):
    for files in sorted([x for x in Path(LOG_FILES_PATH).glob('*.log') if x.is_file()])[:-max_count]:
        files.unlink()


def init_logging(
        stdout_level="INFO",
        file_level="DEBUG",
        write=False,
):
    """

    Parameters
    ----------
    stdout_level :
        Level of the sys.output logging.
    file_level :
        Level of the file logging.
    write :
        If True, writes the logfile to file_path.

    Returns
    -------

    """
    clean_old_log_files()

    formatter = BasicLoggerFormatter()
    handlers = []

    # console
    stdout_handler = logging.StreamHandler(sys.stdout)

    stdout_handler.setLevel(stdout_level.upper())
    stdout_handler.setFormatter(formatter)
    handlers.append(stdout_handler)

    # file
    filename = LOG_FILES_PATH.joinpath(time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())).with_suffix('.log')
    file_handler = logging.FileHandler(filename, delay=not write) # delay=True will write a log only on crash.
    file_handler.setLevel(file_level.upper())
    file_handler.setFormatter(formatter)
    handlers.append(file_handler)

    logging.basicConfig(level="NOTSET", handlers=handlers)

    logging.debug('Logging Started.')

    return filename

