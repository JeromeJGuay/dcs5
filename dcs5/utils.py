import json
from pathlib import PurePath
from typing import *


def dict2json(filename: Union[str, PurePath], dictionary: Dict, indent: int = 4) -> None:
    """Makes json file from dictionary
    Parameters
    ----------
    dictionary
    filename
    indent :
        argument is passed to json.dump(..., indent=indent)
    """
    with open(filename, "w") as f:
        json.dump(dictionary, f, indent=indent)


def json2dict(json_file: Union[str, PurePath]) -> dict:
    """Open json file as a dictionary."""
    with open(json_file) as f:
        dictionary = json.load(f)
    return dictionary


def resolve_relative_path(relative_path, current_path):
    """ """
    return PurePath(current_path).parent.joinpath(relative_path)