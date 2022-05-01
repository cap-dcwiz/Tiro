from collections.abc import Iterable
from pathlib import Path
from typing import Type, Optional

from yaml import safe_load

from .mock import Mocker
from .model import DataPointInfo, Entity
from .utils import split_path, concat_path, snake_to_camel, YAML_META_CHAR, PATH_SEP
from .validate import Validator


class Scenario:
    def __init__(self,
                 *entities: Entity | Type[Entity],
                 asset_library_path: Optional[str] = None,
                 asset_library_name: str = "tiro.assets",
                 **kw_entities: dict[str, Entity | Type[Entity]]):
        self.root: Entity = Entity.create("Scenario",
                                          *entities,
                                          base_class=None,
                                          asset_library_path=asset_library_path,
                                          asset_library_name=asset_library_name,
                                          **kw_entities)()

    @classmethod
    def from_yaml(cls,
                  scenario_data: Path | str,
                  *uses: Path | str):
        if isinstance(scenario_data, Path):
            scenario_data = scenario_data.open().read()
        defs = safe_load(scenario_data)
        asset_library_path = defs.get(f"{YAML_META_CHAR}asset_library_path", None)
        asset_library_name = defs.get(f"{YAML_META_CHAR}asset_library_name", "tiro.assets")
        ins = cls(
            **{k: Entity.create_from_define_string(
                k, v,
                prefix="Scenario",
                asset_library_path=asset_library_path,
                asset_library_name=asset_library_name,
            ) for k, v in defs.items() if not k.startswith(YAML_META_CHAR)}
        )
        for use in uses:
            if isinstance(use, Path):
                use = use.open().read()
            ins.requires(yaml=use)
        return ins

    def __getattr__(self, key):
        return getattr(self.root, key)

    def mocker(self):
        return Mocker(self.root)

    def validator(self, *args, **kwargs):
        return Validator(self.root, *args, **kwargs)

    @classmethod
    def decompose_data(cls, path: str | list[str], value: dict, info=None) -> Iterable[dict]:
        """Decompose a dict to separate data points."""
        path = split_path(path)
        info = info or dict(path="", asset_path="")
        pre_path = info["path"]
        pre_asset_path = info["asset_path"]
        len_prefix = len(path)
        data_point_types = DataPointInfo.SUB_CLASS_NAMES
        if len_prefix == 0:
            for k, v in value.items():
                if k in data_point_types:
                    for sub_k, sub_v in v.items():
                        yield info | \
                              dict(type=k,
                                   field=sub_k,
                                   path=concat_path(pre_path, snake_to_camel(sub_k))) | \
                              sub_v
                elif "type" in info:
                    yield info | dict(field=k)
                else:
                    for sub_k, sub_v in v.items():
                        _info = info | {k: sub_k} | \
                                dict(path=concat_path(pre_path, snake_to_camel(k)),
                                     asset_path=concat_path(pre_asset_path, snake_to_camel(k), sub_k))
                        yield from cls.decompose_data(path, sub_v, _info)
        elif len_prefix == 1:
            for name in data_point_types:
                if path[0] == name:
                    for k, v in value.items():
                        yield info | \
                              dict(type=name,
                                   field=k,
                                   path=concat_path(pre_path, snake_to_camel(k))) | v
                    return
            for k, v in value.items():
                _info = info | {snake_to_camel(path[0]): k} | \
                        dict(path=concat_path(pre_path, snake_to_camel(path[0])),
                             asset_path=concat_path(pre_asset_path, snake_to_camel(path[0]), k))
                yield from cls.decompose_data(path[1:], v, _info)
        else:
            for name in data_point_types:
                if path[0] == name:
                    yield info | \
                          dict(type=name,
                               field=path[1],
                               path=concat_path(pre_path, snake_to_camel(path[1]))) | value
                    return
            _info = info | {snake_to_camel(path[0]): path[1]} | \
                    dict(path=concat_path(pre_path, snake_to_camel(path[0])),
                         asset_path=concat_path(pre_asset_path, snake_to_camel(path[0]), path[1]))
            yield from cls.decompose_data(path[2:], value, _info)

    @staticmethod
    def asset_path_to_path(path: str | list[str]) -> str:
        path = split_path(path)
        return f"{PATH_SEP.join(path[i] for i in range(0, len(path), 2))}{PATH_SEP}{path[-1]}"

    @classmethod
    def asset_path_to_tags(cls, path: str | list[str], tags=None) -> dict:
        tags = tags or dict(path=cls.asset_path_to_path(path), asset_path=path)
        path = split_path(path)
        component = path.pop(0)
        if component in DataPointInfo.SUB_CLASS_NAMES:
            tags |= dict(type=component, field=path[-1])
        else:
            uuid = path.pop(0)
            tags |= {component: uuid}
            cls.asset_path_to_tags(path, tags)
        return tags

    def guess_missing_paths(self, existing_paths=None):
        validator = self.validator(validate_path_only=True,
                                   require_all_children=False)
        if existing_paths:
            for path in existing_paths:
                validator.collect(path, value={})
        res = validator.validate()
        while not res.valid:
            for error in res.exception.errors():
                missing_path = PATH_SEP.join(error["loc"])
                dp_info = self.query_data_point_info(self.asset_path_to_path(missing_path))
                if dp_info:
                    yield missing_path
                validator.collect(missing_path, value={})
            res = validator.validate()
