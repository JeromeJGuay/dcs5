import logging
import os
import platform
from pathlib import Path
import shutil

from dcs5.utils import resolve_relative_path


VERSION = "1.0.0"

### PATHS ###
if platform.system() == 'Windows':
    local_file_path = os.getenv('LOCALAPPDATA') + '/dcs5'
else:
    local_file_path = os.getenv('HOME') + '/.dcs5'


LOG_FILES_PATH = Path(local_file_path).joinpath("logs/")
CONFIG_FILES_PATH = Path(local_file_path).joinpath("configs/")

Path(local_file_path).mkdir(parents=True, exist_ok=True)
LOG_FILES_PATH.mkdir(parents=True, exist_ok=True)
CONFIG_FILES_PATH.mkdir(parents=True, exist_ok=True)

SERVER_CONFIGURATION_FILE = CONFIG_FILES_PATH.joinpath("server_configuration.json")
CONTROLLER_CONFIGURATION_FILE = CONFIG_FILES_PATH.joinpath("controller_configuration.json")
DEVICES_SPECIFICATION_FILE = CONFIG_FILES_PATH.joinpath("devices_specification.json")
CONTROL_BOX_PARAMETERS = CONFIG_FILES_PATH.joinpath("control_box_parameters.json")

DEFAULT_SERVER_CONFIGURATION_FILE = resolve_relative_path("default_configs/server_configuration.json", __file__)
DEFAULT_CONTROLLER_CONFIGURATION_FILE = resolve_relative_path("default_configs/controller_configuration.json", __file__)
DEFAULT_DEVICES_SPECIFICATION_FILE = resolve_relative_path("default_configs/devices_specification.json", __file__)
DEFAULT_CONTROL_BOX_PARAMETERS = resolve_relative_path("default_configs/control_box_parameters.json", __file__)

### LOCAL FILES ###
local_files = [
    SERVER_CONFIGURATION_FILE, CONTROLLER_CONFIGURATION_FILE,
    DEVICES_SPECIFICATION_FILE, CONTROL_BOX_PARAMETERS
]
default_files = [
    DEFAULT_SERVER_CONFIGURATION_FILE, DEFAULT_CONTROLLER_CONFIGURATION_FILE,
    DEFAULT_DEVICES_SPECIFICATION_FILE, DEFAULT_CONTROL_BOX_PARAMETERS
]

for lf, df in zip(local_files, default_files):
    if not Path(lf).exists():
        logging.debug(f'creating local file: {lf}')
        shutil.copyfile(df, lf)
