import logging
import sys
import time
from pathlib import Path

from dcs5.utils import resolve_relative_path

DEFAULT_FILE_PATH = "../logs/dcs5_log"


def init_logging(
        file_path=None,
        stdout_level="INFO",
        file_level="DEBUG",
        write=False,
):
    file_path = resolve_relative_path(DEFAULT_FILE_PATH, __file__) or file_path

    formatter = logging.Formatter("%(asctime)s {%(threadName)s} [%(levelname)s] %(message)s")
    handlers = []

    stdout_handler = logging.StreamHandler(sys.stdout)
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
