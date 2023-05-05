import logging
import os
import platform
from pathlib import Path

from dcs5.utils import resolve_relative_path

VERSION = "1.0.0"

logging.getLogger(__name__)

### LOCAL FILE PATH ###
if platform.system() == 'Windows':
    LOCAL_FILE_PATH = os.getenv('LOCALAPPDATA') + '/dcs5'
else:
    LOCAL_FILE_PATH = os.getenv('HOME') + '/.dcs5'

### LOGGING ###
MAX_COUNT_LOG_FILES = 20
LOG_FILES_PATH = Path(LOCAL_FILE_PATH).joinpath("logs/")

### CONFIG PATH ###
CONFIG_FILES_PATH = Path(LOCAL_FILE_PATH).joinpath("configs/")

Path(LOCAL_FILE_PATH).mkdir(parents=True, exist_ok=True)
LOG_FILES_PATH.mkdir(parents=True, exist_ok=True)
CONFIG_FILES_PATH.mkdir(parents=True, exist_ok=True)

PRINT_COMMAND = "PRINT "
