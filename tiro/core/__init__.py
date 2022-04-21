from functools import partial
from importlib import import_module
from random import randint
from typing import Type

from yaml import safe_load

from tiro.core.model import Entity


def create_entity(name: str,
                  base_path: str,
                  library_path: str = "tiro.assets",
                  **entities) -> Type[Entity]:
    base_path, _, base_name = base_path.rpartition(".")
    if not base_path:
        base = getattr(import_module(library_path), base_name)
    else:
        base = getattr(import_module(f"{library_path}.{base_path}"), base_name)
    return type(name, (base,), dict(__annotations__=entities))


def create_entity_from_dict(name, defs, as_list, prefix=""):
    meta_start = "$"
    if prefix:
        name = f"{prefix}_{name}"
    children = {k: create_entity_from_dict(k, v, as_list=True, prefix=name)
                for k, v in defs.items()
                if not k.startswith(meta_start)}
    entity = create_entity(name, defs[f"{meta_start}type"], **children)
    if as_list:
        list_args = {}
        if f"{meta_start}number" in defs:
            number = defs[f"{meta_start}number"]
            if isinstance(number, str) and "-" in number:
                min_num, max_num = number.split("-")
                list_args["faking_number"] = partial(randint, int(min_num), int(max_num))
            else:
                list_args["faking_number"] = int(number)
        else:
            list_args["faking_number"] = 1
        return entity.many(**list_args)
    else:
        return entity


def create_scenario(*args, **entities):
    ann = {}
    for item in args:
        if isinstance(item, type) and issubclass(item, Entity):
            item = item.many(faking_number=1)
        ann[item.cls.__name__] = item
    for k, v in entities.items():
        if isinstance(v, type) and issubclass(v, Entity):
            v = v.many(faking_number=1)
        ann[k] = v
    return type("Scenario", (Entity,), dict(__annotations__=ann))()


def create_scenario_from_yaml(yaml):
    defs = safe_load(yaml)
    return create_scenario(**{k: create_entity_from_dict(k, v, as_list=True)
                              for k, v in defs.items()})
