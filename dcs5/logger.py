import time
import sys
import logging
from pathlib import Path

DEFAULT_FILE_PATH = "../logs/dcs5_log"


def init_logging(
        verbose="INFO",
        file_path=DEFAULT_FILE_PATH,
        stdout_level="INFO",
        file_level="DEBUG",
        stdout=True,
        write=False,
):
    formatter = logging.Formatter("%(asctime)s {%(threadName)s} [%(levelname)s] %(message)s")
    handlers = []

    if stdout is True:
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(stdout_level.upper())
        stdout_handler.setFormatter(formatter)
        handlers.append(stdout_handler)

    if write is True:
        file_handler = logging.FileHandler(format_log_path(file_path))
        file_handler.setLevel(file_level.upper())
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    logging.basicConfig(level=verbose.upper(), handlers=handlers)


def format_log_path(path: str) -> str:
    new_stem = Path(path).stem + "_" + time.strftime("%y%m%dT%H%M%S", time.gmtime())
    return str(Path(path).parent.joinpath(Path(new_stem)).with_suffix('.log'))
