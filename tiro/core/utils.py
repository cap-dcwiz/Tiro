from copy import copy
from pathlib import Path
from typing import Any, Iterable

import yaml

PATH_SEP = "."
YAML_META_CHAR = "$"


def concat_path(*components):
    return PATH_SEP.join(components).strip(PATH_SEP)


def split_path(path: str | list[str]) -> list[str]:
    if isinstance(path, str):
        if path:
            path = path.split(PATH_SEP)
        else:
            path = []
    return path


def snake_to_camel(name: str) -> str:
    # Not doing anything, need to fix or change the function name.
    return name


def camel_to_snake(name: str) -> str:
    # Not doing anything, need to fix or change the function name.
    return name


DataPointTypes = int, float, str


def insert_data_point_to_dict(path: str | list[str], value: Any, data: dict):
    path = split_path(path)
    component = path.pop(0)
    if not path:
        data[component] = copy(value)
    else:
        if component not in data:
            data[component] = {}
        insert_data_point_to_dict(path, value, data[component])


def decouple_uses(uses_data: str | dict | Path) -> Iterable[str]:
    if isinstance(uses_data, Path):
        uses_data = yaml.safe_load(uses_data.open())
    for item in uses_data:
        if isinstance(item, str):
            yield item
        else:
            for k, v in item.items():
                for _path in decouple_uses(v):
                    yield k + PATH_SEP + _path


def format_regex(pattern):
    pattern = pattern.replace("%%", ".*")
    pattern = pattern.replace("%", "\.")
    return f"^{pattern}$"
