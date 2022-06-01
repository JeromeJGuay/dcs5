"""
Module that contains the scripts to load controller configuration.

"""
import logging
from utils import json2dict, resolve_relative_path
from typing import *

DEFAULT_CONTROLLER_CONFIGURATION_FILE = resolve_relative_path('src_files/controller_configurations.json', __file__)


class BasicConfig:
    def __init__(self):
        self.platform_type: str = None
        self.device_name: str = None
        self.mac_address: str = None


class Dcs5Config(BasicConfig):
    def __init__(self):
        super().__init__()
        self.board_decal: str = None
        self.control_box_model: str = None
        self.control_box_decal: str = None
        self.launch_settings: Dcs5LaunchSettings = None
        self.stylus: List[str] = None
        self.board_output: Dcs5BoardOutput = None
        self.reading_profile: Dict[str: Dcs5ReadingProfile]
        self.reading_profile_map: Dict[str, str] = None
        self.controller_keys_map: Dict[str, str] = None
        self.board_keys_map: Dict[str, str] = None


class Dcs5BoardOutput:
    def __init__(self):
        self.swipe_threshold: int = None
        self.segments: list = None
        self.zones: list = None


class Dcs5ReadingProfile:
    def __init__(self):
        self.settling_delay: int = None
        self.number_of_reading: int = None
        self.max_deviation: int = None


class Dcs5LaunchSettings:
    def __init__(self):
        self.board_output_zone: str = None
        self.dynamic_stylus_mode: bool = False
        self.backlighting_level: int = None
        self.backlighting_auto_mode: bool = None
        self.backlighting_sensitivity: int = None


def load_controller_configuration(filename: str, config_name: str):
    config_file = json2dict(filename)
    if config_name in config_file:
        device_config = config_file[config_name]
        key, sub_key = None, None
        try:
            if device_config['platform_type'] == "dcs5":
                controller_config = Dcs5Config()
                for key in controller_config.__dict__:
                    if controller_config.__dict__[key] is not None:
                        for sub_key in controller_config.__dict__[key].__dict__:
                            controller_config.__dict__[key].__dict__[sub_key] = device_config[key][sub_key]
                    else:
                        controller_config.__dict__[key] = device_config[key]
                return controller_config
            else:
                logging.error(f"Invalid Controller config. {device_config['platform']} not a platform.")
                return None
        except KeyError:
            logging.error(f"Invalid Controller config. {[key, sub_key]}")
            return None
    else:
        logging.error(f'{config_name} not found in {filename}')
        return None


if __name__ == "__main__":
    c = load_controller_configuration(DEFAULT_CONTROLLER_CONFIGURATION_FILE, 'default_dcs5')