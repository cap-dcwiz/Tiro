import re
from copy import copy


def camel_to_snake(name: str) -> str:
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


DataPointTypes = int, float, str


def insert_into(data: dict, path: str | list[str], value) -> dict:
    if isinstance(path, str):
        if path:
            path = path.split(".")
        else:
            path = []
    component = path.pop(0)
    if not path:
        data[component] = copy(value)
    else:
        if component not in data:
            data[component] = {}
        insert_into(data[component], path, value)
    return data
