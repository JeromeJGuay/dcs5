from dataclasses import dataclass
from typing import Dict, List
from utils import json2dict


@dataclass
class Board:
    number_of_keys: int
    key_to_mm_ratio: float
    zero: float
    detection_range: float
    relative_zero: float
    keys_layout: Dict[str, List[str]]
    mappable_keys: List[str]

    def __post_init__(self):
        self.relative_zero = self.zero - self.detection_range


@dataclass
class ControlBox:
    keys_layout: Dict[str, str]
    mappable_keys: List[str]


@dataclass
class DevicesSpecification:
    board: Board
    control_box: ControlBox
    stylus_offset: Dict[str, str]

    def __post_init__(self):
        self.board = Board(**self.board)
        self.control_box = ControlBox(**self.control_box)


def load_devices_specification(path: str):
    specification = json2dict(path)
    return DevicesSpecification(**specification)

