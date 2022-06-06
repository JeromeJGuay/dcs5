"""
Module that contains the scripts to load controller configuration.

"""
from dataclasses import dataclass
from utils import json2dict
from typing import *
from controller import VALID_COMMANDS, VALID_KEYBOARD_KEYS, VALID_SEGMENTS_MODE


class ConfigError(Exception):
    pass


@dataclass
class Client:
    device_name: str
    mac_address: str


@dataclass
class LaunchSettings:
    output_mode: str
    dynamic_stylus_mode: bool
    reading_profile: str
    backlighting_level: int
    backlighting_auto_mode: bool
    backlighting_sensitivity: int
    length_units: str


@dataclass
class ReadingProfile:
    settling_delay: int
    number_of_reading: int
    max_deviation: int


@dataclass
class ModeReadingProfiles:
    top: str
    length: str
    bottom: str


@dataclass
class OutputModes:
    swipe_threshold: int
    segments_limits: List[int]
    segments_mode: List[str]
    mode_reading_profiles: ModeReadingProfiles

    def __post_init__(self):
        self.mode_reading_profiles = ModeReadingProfiles(**self.mode_reading_profiles)
        if len(self.segments_limits) - 1 != len(self.segments_mode):
            raise ConfigError('`segments_limits` needs to have one more element than `segments_mode`.')
        if any(m not in VALID_SEGMENTS_MODE for m in self.segments_mode):
            raise ConfigError(f'`segments_mode` value must be in {VALID_SEGMENTS_MODE}')


@dataclass
class KeyMaps:
    control_box: Dict[str, str]
    board: Dict[str, str]

    def __post_init__(self):
        self.check_key_map(self.control_box)
        self.check_key_map(self.board)

    @staticmethod
    def check_key_map(key_map: Dict[str, str]):
        for key, value in key_map:
            if value is not None and value not in VALID_KEYBOARD_KEYS + VALID_COMMANDS:
                raise ConfigError(f"Invalid KeyBoard key: {key} -> {value}.")


@dataclass
class ControllerConfiguration:
    client: Client
    launch_settings: LaunchSettings
    reading_profiles: Dict[str, ReadingProfile]
    output_modes: OutputModes
    key_maps: KeyMaps

    def __post_init__(self):
        self.client = Client(**self.client)
        self.launch_settings = LaunchSettings(**self.launch_settings)
        self.reading_profiles = {k: ReadingProfile(**v) for k, v in self.reading_profiles.items()}
        self.output_modes = OutputModes(**self.output_modes)
        self.key_maps = KeyMaps(self.key_maps)


def load_config(path: str):
    configurations = json2dict(path)
    return ControllerConfiguration(**configurations)
