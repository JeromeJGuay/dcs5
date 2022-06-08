import time
import sys
import logging
from pathlib import Path

DEFAULT_FILE_PATH = "../logs/dcs5_log"


def init_logging(
        verbose: str = 'INFO',
        file_path: str = DEFAULT_FILE_PATH,
        stdout_level: str = "INFO",
        file_level: str = "DEBUG",
        write=False
        ):

    logger = logging
    logger.setLevel(verbose)

    formatter = logging.Formatter("%(asctime)s {%(threadName)s} [%(levelname)s] %(message)s")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(stdout_level)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    if write is True:
        file_handler = logging.FileHandler(format_log_path(file_path))
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def format_log_path(path: str) -> str:
    new_stem = Path(path).stem + "_" + time.strftime("%y%m%dT%H%M%S", time.gmtime())
    return str(Path(path).parent.joinpath(Path(new_stem)).with_suffix('.log'))


