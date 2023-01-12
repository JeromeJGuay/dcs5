from dataclasses import dataclass

from dcs5.utils import json2dict

from json.decoder import JSONDecodeError



@dataclass
class BaseControlBoxParameters:
    settling_delay = 1
    max_deviation = 6
    number_of_reading = 5
    min_settling_delay = 0
    max_settling_delay = 20
    min_max_deviation = 1
    max_max_deviation = 100

@dataclass
class XtControlBoxParameters(BaseControlBoxParameters):
    backlight_level = 0
    backlighting_auto_mode = False
    backlighting_sensitivity = 0
    max_backlighting_level = 95
    max_backlighting_sensitivity = 7


@dataclass
class MicroControlBoxParameters(BaseControlBoxParameters):
    backlight_level = 0
    max_backlighting_level = 95


#
# @dataclass
# class ControlBoxParameters:
#     settling_delay: int
#     max_deviation: int
#     number_of_reading: int
#     backlight_level: int
#     backlighting_auto_mode: int
#     backlighting_sensitivity: int
#     min_settling_delay: int
#     max_settling_delay: int
#     min_max_deviation: int
#     max_max_deviation: int
#     max_backlighting_level: int
#     max_backlighting_sensitivity: int
#
#
# def load_control_box_parameters(path: str):
#     settings = json2dict(path)
#     try:
#         return ControlBoxParameters(**settings)
#     except (JSONDecodeError, TypeError):  # Catch JsonError Missing keys error.
#         return None
#
