from dataclasses import dataclass

from dcs5.utils import json2dict

from json.decoder import JSONDecodeError

@dataclass
class ControlBoxParameters:
    settling_delay: int
    max_deviation: int
    number_of_reading: int
    backlight_level: int
    backlighting_auto_mode: int
    backlighting_sensitivity: int
    min_settling_delay: int
    max_settling_delay: int
    min_max_deviation: int
    max_max_deviation: int
    max_backlighting_level: int
    max_backlighting_sensitivity: int


def load_control_box_parameters(path: str):
    settings = json2dict(path)
    try:
        return ControlBoxParameters(**settings)
    except (JSONDecodeError, TypeError):  # Catch JsonError Missing keys error.
        return None

