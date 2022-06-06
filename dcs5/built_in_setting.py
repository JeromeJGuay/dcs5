from dataclasses import dataclass
from utils import json2dict


@dataclass
class Settings:
    settling_delay: int
    max_deviation: int
    number_of_reading: int
    backlight_level: int
    backlighting_auto_mode: int
    backlighting_sensitivity: int
    max_settling_delay: int
    max_max_deviation: int
    min_backlighting_level: int
    max_backlighting_level: int
    min_backlighting_sensitivity: int
    max_backlighting_sensitivity: int


def load_built_in_settings(path: str):
    settings = json2dict(path)
    return Settings(**settings)

