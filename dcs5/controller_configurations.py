"""
Module that contains the scripts to load the board configurations.

Valid commands :
    ["BACKLIGHT_UP", "BACKLIGHT_DOWN", "CHANGE_STYLUS", "UNITS_mm", "UNITS_cm", "MODE",
    "CHANGE_OUTPUT_MODE", "MODE_TOP", "MODE_LENGTH", "MODE_BOTTOM", "WEIGHT"]
 - The "MODE" command is not a command per say but a MetaKey for the board.
 - The "CHANGE_OUTPUT_MODE" command will cycle through MODE_LENGTH, MODE_TOP, MODE_BOTTOM
Valid keyboard inputs :
     'print <string to print>'

     and

    ['\t', '\n', '\r', ' ', '!', '"', '#', '$', '%', '&', "'",
    '(', ')', '*', '+', ',', '-', '.', '/', '{', '|', '}', '~',
    ':', ';', '<', '=', '>', '?', '@', '[', '\\', ']', '^', '_', '`',
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o',
    'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O',
    'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'
                                                      'accept', 'add', 'alt', 'altleft', 'altright', 'apps',
    'backspace',
    'browserback', 'browserfavorites', 'browserforward', 'browserhome',
    'browserrefresh', 'browsersearch', 'browserstop', 'capslock', 'clear',
    'convert', 'ctrl', 'ctrlleft', 'ctrlright', 'decimal', 'del', 'delete',
    'divide', 'down', 'end', 'enter', 'esc', 'escape', 'execute', 'f1', 'f10',
    'f11', 'f12', 'f13', 'f14', 'f15', 'f16', 'f17', 'f18', 'f19', 'f2', 'f20',
    'f21', 'f22', 'f23', 'f24', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9',
    'final', 'fn', 'hanguel', 'hangul', 'hanja', 'help', 'home', 'insert', 'junja',
    'kana', 'kanji', 'launchapp1', 'launchapp2', 'launchmail',
    'launchmediaselect', 'left', 'modechange', 'multiply', 'nexttrack',
    'nonconvert', 'num0', 'num1', 'num2', 'num3', 'num4', 'num5', 'num6',
    'num7', 'num8', 'num9', 'numlock', 'pagedown', 'pageup', 'pause', 'pgdn',
    'pgup', 'playpause', 'prevtrack', 'print', 'printscreen', 'prntscrn',
    'prtsc', 'prtscr', 'return', 'right', 'scrolllock', 'select', 'separator',
    'shift', 'shiftleft', 'shiftright', 'sleep', 'space', 'stop', 'subtract', 'tab',
    'up', 'volumedown', 'volumemute', 'volumeup', 'win', 'winleft', 'winright', 'yen',
    'command', 'option', 'optionleft', 'optionright']
"""
from json.decoder import JSONDecodeError
from dataclasses import dataclass
from typing import *

from dcs5.utils import json2dict

VALID_COMMANDS = ["BACKLIGHT_UP", "BACKLIGHT_DOWN", "CHANGE_STYLUS", "UNITS_mm", "UNITS_cm", "MODE",
                  "CHANGE_OUTPUT_MODE", "MODE_TOP", "MODE_LENGTH", "MODE_BOTTOM", "WEIGHT"]
VALID_SEGMENTS_MODE = ['length', 'top', 'bottom']
VALID_KEYBOARD_KEYS = [
    '\t', '\n', '\r', ' ', '!', '"', '#', '$', '%', '&', "'",
    '(', ')', '*', '+', ',', '-', '.', '/', '{', '|', '}', '~',
    ':', ';', '<', '=', '>', '?', '@', '[', '\\', ']', '^', '_', '`',
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o',
    'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O',
    'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'
                                                      'accept', 'add', 'alt', 'altleft', 'altright', 'apps',
    'backspace',
    'browserback', 'browserfavorites', 'browserforward', 'browserhome',
    'browserrefresh', 'browsersearch', 'browserstop', 'capslock', 'clear',
    'convert', 'ctrl', 'ctrlleft', 'ctrlright', 'decimal', 'del', 'delete',
    'divide', 'down', 'end', 'enter', 'esc', 'escape', 'execute', 'f1', 'f10',
    'f11', 'f12', 'f13', 'f14', 'f15', 'f16', 'f17', 'f18', 'f19', 'f2', 'f20',
    'f21', 'f22', 'f23', 'f24', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9',
    'final', 'fn', 'hanguel', 'hangul', 'hanja', 'help', 'home', 'insert', 'junja',
    'kana', 'kanji', 'launchapp1', 'launchapp2', 'launchmail',
    'launchmediaselect', 'left', 'modechange', 'multiply', 'nexttrack',
    'nonconvert', 'num0', 'num1', 'num2', 'num3', 'num4', 'num5', 'num6',
    'num7', 'num8', 'num9', 'numlock', 'pagedown', 'pageup', 'pause', 'pgdn',
    'pgup', 'playpause', 'prevtrack', 'print', 'printscreen', 'prntscrn',
    'prtsc', 'prtscr', 'return', 'right', 'scrolllock', 'select', 'separator',
    'shift', 'shiftleft', 'shiftright', 'sleep', 'space', 'stop', 'subtract', 'tab',
    'up', 'volumedown', 'volumemute', 'volumeup', 'win', 'winleft', 'winright', 'yen',
    'command', 'option', 'optionleft', 'optionright'
]
VALID_UNITS = ["mm", "cm"]


def check_key_map(key_map: Dict[str, str]):
    for key, value in key_map.items():
        validate_command(key, value)


def validate_command(key, value):
    if isinstance(value, list):
        for _value in value:
            validate_command(key, _value)
    elif value not in [None, ""]:
        if value.startswith('print '):
            pass
        else:
            if value not in VALID_KEYBOARD_KEYS + VALID_COMMANDS:
                raise ConfigError(f"Invalid Command or KeyBoard key: {key} -> {value}.")


class ConfigError(Exception):
    pass
    # def __init__(self, error: str):
    #     self.error = error


@dataclass
class Client:
    device_name: str
    mac_address: str
    marel_ip_address: str


@dataclass
class LaunchSettings:
    output_mode: str
    dynamic_stylus_mode: bool
    reading_profile: str
    backlighting_level: int
    #backlighting_auto_mode: bool
    #backlighting_sensitivity: int
    length_units: str
    stylus: str
    auto_enter: bool

    def __post_init__(self):
        if self.length_units not in VALID_UNITS:
            raise ConfigError(f'Invalid value for `launch_settings/length_units`. Must be one of {VALID_UNITS}')
        if not isinstance(self.dynamic_stylus_mode, bool):
            raise ConfigError('Invalid value for `launch_settings/dynamic_stylus_mode`. Must but in (true/false)')
        if not isinstance(self.auto_enter, bool):
            raise ConfigError('Invalid value for `launch_settings/auto_enter`. Must but in (true/false)')
        #if not isinstance(self.backlighting_auto_mode, bool):
        #    raise ConfigError('Invalid value for `launch_settings/back_light_auto_mode`. Must but in (true/false)')


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

    def __getitem__(self, item):
        return getattr(self, item)


@dataclass
class OutputModes:
    swipe_threshold: int
    segments_limits: List[int]
    segments_mode: List[str]
    mode_reading_profiles: ModeReadingProfiles

    def __post_init__(self):
        self.mode_reading_profiles = ModeReadingProfiles(**self.mode_reading_profiles)
        if len(self.segments_limits) - 1 != len(self.segments_mode):
            raise ConfigError('Invalid value for `output_modes/segments_limits`. It needs to have one more element than `segments_mode`.')
        if any(m not in VALID_SEGMENTS_MODE for m in self.segments_mode):
            raise ConfigError(f'Invalid value for `outputs_modes/segments_mode`. Must be in {VALID_SEGMENTS_MODE}')


@dataclass
class KeyMaps:
    control_box: Dict[str, str]
    control_box_mode: Dict[str, str]
    board: Dict[str, str]
    board_mode: Dict[str, str]

    def __post_init__(self):
        check_key_map(self.control_box)
        check_key_map(self.board)
        check_key_map(self.control_box_mode)
        check_key_map(self.board_mode)


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
        self.key_maps = KeyMaps(**self.key_maps)

        if self.launch_settings.reading_profile not in self.reading_profiles:
            raise ConfigError('Invalid value for  `launch_settings/reading_profile`. Value not in reading_profiles.')
        if self.output_modes.mode_reading_profiles.top not in self.reading_profiles:
            raise ConfigError('Invalid value for  `output_mode/mode_reading_profile/top`. Value not in reading_profiles.')
        if self.output_modes.mode_reading_profiles.length not in self.reading_profiles:
            raise ConfigError('Invalid value for  `output_mode/mode_reading_profile/length`. Value not in reading_profiles.')
        if self.output_modes.mode_reading_profiles.bottom not in self.reading_profiles:
            raise ConfigError('Invalid value for  `output_mode/mode_reading_profile/bottom`. Value not in reading_profiles.')


def load_config(path: str):
    try:
        return ControllerConfiguration(**json2dict(path))
    except (JSONDecodeError, TypeError):  # Catch JsonError Missing keys error.
        return None


