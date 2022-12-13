from dataclasses import dataclass
from typing import Dict, List

from dcs5.utils import json2dict

from json.decoder import JSONDecodeError

CONTROL_BOX_MODELS = ['xt', 'micro']


class ConfigError(Exception):
    pass


@dataclass
class Board:
    number_of_keys: int
    key_to_mm_ratio: float
    zero: float
    detection_range: float
    keys_layout: Dict[str, List[str]]

    def __post_init__(self):
        self.relative_zero = self.zero - self.detection_range


@dataclass
class ControlBox:
    model: str
    keys_layout: Dict[str, str]

    def __post_init__(self):
        if self.model not in CONTROL_BOX_MODELS:
            raise ConfigError(f'Invalid value for `control_box/model`. Must be in {CONTROL_BOX_MODELS}')


@dataclass
class DevicesSpecifications:
    board: Board
    control_box: ControlBox
    stylus_offset: Dict[str, str]

    def __post_init__(self):
        self.board = Board(**self.board)
        self.control_box = ControlBox(**self.control_box)


def load_devices_specification(path: str):
    specification = json2dict(path)
    try:
        return DevicesSpecifications(**specification)
    except (JSONDecodeError, TypeError):  # Catch JsonError Missing keys error.
        return None

