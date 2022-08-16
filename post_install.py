import shutil
from pathlib import Path
import click

from dcs5 import \
    SERVER_CONFIGURATION_FILE, \
    CONTROLLER_CONFIGURATION_FILE, \
    DEVICES_SPECIFICATION_FILE, \
    CONTROL_BOX_PARAMETERS_FILE, \
    DEFAULT_SERVER_CONFIGURATION_FILE, \
    DEFAULT_CONTROLLER_CONFIGURATION_FILE, \
    DEFAULT_DEVICES_SPECIFICATION_FILE, \
    DEFAULT_CONTROL_BOX_PARAMETERS

local_files = [
    SERVER_CONFIGURATION_FILE, CONTROLLER_CONFIGURATION_FILE,
    DEVICES_SPECIFICATION_FILE, CONTROL_BOX_PARAMETERS_FILE
]
default_files = [
    DEFAULT_SERVER_CONFIGURATION_FILE, DEFAULT_CONTROLLER_CONFIGURATION_FILE,
    DEFAULT_DEVICES_SPECIFICATION_FILE, DEFAULT_CONTROL_BOX_PARAMETERS
]


def create_local_files():
    print('\n\n')
    overwrite_files = None
    for lf, df in zip(local_files, default_files):
        if not Path(lf).exists():
            shutil.copyfile(df, lf)
        else:
            if overwrite_files is None:
                overwrite_files=True #FIXME
                #overwrite_files = click.confirm('Overwrite reinstall local files ?')
            if overwrite_files:
                shutil.copyfile(df, lf)
                print(f'Writing file: {lf}')
