import json
from typing import *
from pathlib import Path


def dict2json(filename: str, dictionary: Dict, indent: int = 4) -> None:
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


def json2dict(json_file: Union[str, Path])->dict:
    """Open json file as a dictionary."""
    with open(json_file) as f:
        dictionary = json.load(f)
    return dictionary
