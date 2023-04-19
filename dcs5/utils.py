"""
This modules contains some utils for path handling and json files.
"""
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


def update_json_value(filename, key_path: List[str], value):
    data = json2dict(filename)

    tree = data
    for k in key_path[:-1]:
        tree = tree[k]
    tree[key_path[-1]] = value

    dict2json(filename, data)
