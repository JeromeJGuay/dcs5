import os
import platform
from pathlib import Path


from dcs5.utils import resolve_relative_path


VERSION = "1.0.0"

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

SERVER_CONFIGURATION_FILE_NAME = "server_configuration.json"
CONTROLLER_CONFIGURATION_FILE_NAME = 'controller_configuration.json'
DEVICES_SPECIFICATION_FILE_NAME = 'devices_specification.json'
CONTROL_BOX_PARAMETERS_FILE_NAME = "control_box_parameters.json"

DEFAULT_CONFIG_PATH = "default_configs/"

DEFAULT_CONTROLLER_CONFIGURATION_FILE = str(resolve_relative_path(DEFAULT_CONFIG_PATH + CONTROLLER_CONFIGURATION_FILE_NAME, __file__))
DEFAULT_DEVICES_SPECIFICATION_FILE = str(resolve_relative_path(DEFAULT_CONFIG_PATH + DEVICES_SPECIFICATION_FILE_NAME, __file__))
DEFAULT_CONTROL_BOX_PARAMETERS_FILE = str(resolve_relative_path(DEFAULT_CONFIG_PATH + CONTROL_BOX_PARAMETERS_FILE_NAME, __file__))

USER_GUIDE_FILE = str(resolve_relative_path('static/UserGuide_fr.pdf', __file__))

LOGO_PATH = str(resolve_relative_path('static/bigfin_logo.png', __file__))
