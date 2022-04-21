from copy import copy
from typing import Any

PATH_SEP = "."


def concat_path(*components):
    return PATH_SEP.join(components).strip(PATH_SEP)


def split_path(path):
    if isinstance(path, str):
        if path:
            path = path.split(PATH_SEP)
        else:
            path = []
    return path


def snake_to_camel(name: str) -> str:
    return name
    # return "".join([x.capitalize() for x in name.split("_")])


def camel_to_snake(name: str) -> str:
    return name
    # name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    # return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


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
