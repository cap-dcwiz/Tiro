import re
import sys
from collections.abc import Iterable
from datetime import datetime, timedelta
from functools import partial
from importlib import import_module
from inspect import get_annotations
from pathlib import Path
from random import randint
from typing import TypeVar, Generic, Optional, Type, Any, Union, Callable, Literal, Generator

from pydantic import BaseModel, create_model, Field
from pydantic.generics import GenericModel
from yaml import safe_load

from .utils import camel_to_snake, DataPointTypes, PATH_SEP, concat_path, YAML_META_CHAR, split_path, decouple_uses, \
    format_regex

DPT = TypeVar("DPT", *DataPointTypes)


class EntityList:
    """Holding the information of a list of entity with the same type"""

    def __init__(self,
                 cls: Type["Entity"],
                 faking_number: Optional[Callable | int] = None,
                 ids: Optional[list[str]] = None
                 ):
        self.cls = cls
        self.ids = ids
        if self.ids is not None:
            if faking_number is None:
                faking_number = len(self.ids)
            elif isinstance(faking_number, int) and faking_number > len(self.ids):
                raise RuntimeError("When ids is provided, faking_number must be less than the length of ids.")
        if isinstance(faking_number, int):
            self.number_faker = lambda: faking_number
        else:
            self.number_faker = faking_number

    def new_entity(self, parent: Optional["Entity"] = None) -> "Entity":
        """Generate an entity instance"""
        return self.cls(parent)


class DataPoint(GenericModel, Generic[DPT]):
    """Base Pydantic Model to representing a data point"""
    value: DPT
    timestamp: datetime
    _unit: Optional[str] = None

    class Config:
        @staticmethod
        def schema_extra(schema: dict[str, Any], model: Type["DataPoint"]) -> None:
            schema["unit"] = model._unit
            for p in schema["properties"].values():
                p.pop("title", None)


class DataPointInfo:
    SUB_CLASSES = set()
    SUB_CLASS_NAMES = set()

    def __init__(self,
                 type: Any,
                 unit: Optional[str] = None,
                 faker: Optional[Callable] = None,
                 time_var: Optional[timedelta] = timedelta(seconds=0),
                 default=None):
        self.type = type
        self.unit = unit
        self.faker = faker
        self.time_var = time_var
        self.default = default

    def __init_subclass__(cls, **kwargs):
        cls.SUB_CLASSES.add(cls)
        cls.SUB_CLASS_NAMES.add(cls.__name__)

    def default_object(self, cls: Optional[Type[DataPoint]] = None) -> Optional[DataPoint | dict]:
        if self.default is None:
            return None
        else:
            current_time = datetime.utcnow().isoformat()
            if cls:
                return cls(value=self.default, timestamp=current_time, _unit=self.unit)
            else:
                return dict(value=self.default, timestamp=current_time, unit=self.unit)


class Telemetry(DataPointInfo):
    """Data point that dynamically changes."""
    pass


class Attribute(DataPointInfo):
    """Data point that seldom changes"""
    pass


class RequireHelper:
    """Helper class for requiring children or data points"""

    def __init__(self, component: str, parent: Union["RequireHelper", "Entity"]):
        self.component = component
        self.parent = parent

    @property
    def path(self) -> str:
        if isinstance(self.parent, RequireHelper):
            return f"{self.parent.path}.{self.component}"
        else:
            return self.component

    @property
    def origin(self) -> Union["RequireHelper", "Entity"]:
        if isinstance(self.parent, RequireHelper):
            return self.parent.origin
        else:
            return self.parent

    def __getattr__(self, item):
        return RequireHelper(item, self)

    def use(self) -> "Entity":
        return self.origin.requires(self.path)


class Entity:
    class Config:
        @staticmethod
        def schema_extra(schema: dict[str, Any], model: Type["Entity"]) -> None:
            schema.pop("title", None)
            for p in schema["properties"].values():
                p.pop("title", None)

    data_point_info: dict[str, DataPointInfo] = {}

    def __init_subclass__(cls, **kwargs):
        super(Entity, cls).__init_subclass__(**kwargs)
        cls.data_point_info = {}
        for c in cls.__mro__:
            if issubclass(c, Entity):
                cls.data_point_info |= c.data_point_info
        cls.child_info: dict[str, EntityList] = {}
        for k, v in get_annotations(cls).items():
            if isinstance(v, DataPointInfo):
                cls.data_point_info[k] = v
                if hasattr(cls, k):
                    v.default = getattr(cls, k)
                    delattr(cls, k)
            elif isinstance(v, EntityList):
                cls.child_info[k] = v
                if hasattr(cls, k):
                    delattr(cls, k)
        cls.cached_data_point_model = {}

    def __init__(self,
                 parent: Optional["Entity"] = None,
                 ):
        self.children: dict[str, Entity] = {}
        self.parent: Optional[Entity] = parent
        self._used_data_points: set[str] = set()
        self.uses = set()

    @classmethod
    def many(cls, *args, **kwargs) -> EntityList:
        """Return a list of the entities with the same type"""
        return EntityList(cls, *args, **kwargs)

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def unique_name(self) -> str:
        if self.parent and "_" not in self.name:
            unique_name = f"{self.parent.unique_name}_{self.__class__.__name__}"
        else:
            unique_name = self.name
        return unique_name

    def _parse_use_yaml(self, d, prefix="") -> Generator[str, None, None]:
        if isinstance(d, list):
            for item in d:
                yield from self._parse_use_yaml(item, prefix=prefix)
        elif isinstance(d, dict):
            for k, v in d.items():
                yield from self._parse_use_yaml(v, prefix=concat_path(prefix, k))
        elif isinstance(d, str):
            yield concat_path(prefix, d)

    def requires(self, *paths: str, yaml: str | Path = None) -> "Entity":
        """
        Mark a series of data points are required in a use case.
        A path is a string like Scenario.Room.Server.CPUTemperature.
        Alternatively, a yaml string or path can be provided.
        """
        paths = list(paths)
        if yaml:
            if isinstance(yaml, Path):
                yaml = yaml.open().read()
            paths.extend(self._parse_use_yaml(safe_load(yaml)))
        for path in paths:
            self.uses.add(path)
            if PATH_SEP in path:
                entity, _, path = path.partition(PATH_SEP)
                if entity not in self.children:
                    self.children[entity] = self.child_info[entity].new_entity(self)
                self.children[entity].requires(path)
            else:
                if path in self.data_point_info:
                    self._used_data_points.add(path)
                elif path in self.child_info and path not in self.children:
                    self.children[path] = self.child_info[path].new_entity(self)
        return self

    @classmethod
    def update_defaults(cls, **defaults):
        for key, value in defaults.items():
            cls.data_point_info[key].default = value

    def _create_date_points_model(self,
                                  dp_category: Type[DataPoint],
                                  hide_dp_values: bool
                                  ) -> tuple[Optional[Type[BaseModel]], bool]:
        """Dynamically generate Pydantic model for all data points in the entity."""
        info = {k: v for k, v in self.data_point_info.items()
                if isinstance(v, dp_category) and k in self._used_data_points}
        if not info:
            return None, False
        sub_models: dict[str, tuple[type, Any]] = {}
        is_optional = True
        for dp_name, dp_info in info.items():
            dp_model_name = f"{self.name}_{dp_name}"
            if hide_dp_values:
                dp_type = dict
            else:
                model_cache = self.__class__.cached_data_point_model
                if dp_model_name not in model_cache:
                    model_cache[dp_model_name] = type(f"{self.name}_{dp_name}",
                                                      (DataPoint[dp_info.type],),
                                                      dict(_unit=dp_info.unit))
                dp_type = model_cache[dp_model_name]
            if dp_info.default is not None and not hide_dp_values:
                sub_models[camel_to_snake(dp_name)] = Optional[dp_type], dp_info.default_object(dp_type)
            else:
                is_optional = False
                sub_models[camel_to_snake(dp_name)] = dp_type, ...
        return create_model(f"{self.unique_name}_{dp_category.__name__}", **sub_models), is_optional

    def _create_entities_model(self,
                               hide_dp_values: bool,
                               require_all_children: bool
                               ) -> tuple[dict[str, tuple[type, Any]], bool]:
        """Dynamically generate Pydantic model for the entity type."""
        fields = {}
        is_optional = True
        for name, ins in self.children.items():
            sub_model_list_values, sub_is_optional = ins._model(hide_dp_values=hide_dp_values,
                                                                require_all_children=require_all_children)
            child_info = self.child_info[name]
            if child_info.ids:
                sub_model_list = dict[Literal[tuple(child_info.ids)], sub_model_list_values]
            else:
                sub_model_list = dict[str, sub_model_list_values]
            if sub_is_optional and not require_all_children:
                fields[camel_to_snake(name)] = Optional[sub_model_list], {}
            else:
                is_optional = False
                fields[camel_to_snake(name)] = sub_model_list, ...
        return fields, is_optional

    def _model(self, hide_dp_values: bool, require_all_children: bool) -> tuple[Type[BaseModel], bool]:
        """Generate a complete Pydantic model for a model tree staring from current entity."""
        fields, is_optional = self._create_entities_model(hide_dp_values=hide_dp_values,
                                                          require_all_children=require_all_children)
        for dp_category in DataPointInfo.SUB_CLASSES:
            dp_model, sub_is_optional = self._create_date_points_model(dp_category, hide_dp_values=hide_dp_values)
            if dp_model:
                if sub_is_optional:
                    fields |= {camel_to_snake(dp_category.__name__): (Optional[dp_model], {})}
                else:
                    fields |= {camel_to_snake(dp_category.__name__): (dp_model, ...)}
                is_optional &= sub_is_optional
        return create_model(self.unique_name, config=self.Config, **fields), is_optional

    def model(self, hide_dp_values: bool = False, require_all_children: bool = True):
        return self._model(hide_dp_values=hide_dp_values, require_all_children=require_all_children)[0]

    def __getattr__(self, item: str) -> RequireHelper:
        return RequireHelper(item, self)

    def data_points(self, used_only: bool = True) -> list[str]:
        if used_only:
            return list(self._used_data_points)
        else:
            return list(self.data_point_info.keys())

    def query_data_point_info(self, path: str | list[str]):
        path = split_path(path)
        if path:
            if path[0] in self.children.keys():
                return self.children[path[0]].query_data_point_info(path[1:])
            elif path[0] in self.data_point_info:
                return self.data_point_info[path[0]]

    def default_values(self, path: str | list[str]):
        path = split_path(path)
        if path:
            if path[0] in self.children.keys():
                return self.children[path[0]].default_values(path[1:])
            else:
                return {}
        else:
            res = {}
            for k in self._used_data_points:
                dp_info = self.data_point_info[k]
                if dp_info.default:
                    res[k] = dp_info.default_object() | dict(type=dp_info.__class__.__name__)
            return res

    @classmethod
    def use_selection_model(cls, name_prefix=""):
        telemetry_names = tuple(k for k, v in cls.data_point_info.items() if isinstance(v, Telemetry))
        attribute_names = tuple(k for k, v in cls.data_point_info.items() if isinstance(v, Attribute))
        name = f"{name_prefix}.{cls.__name__}".strip(".")
        model_kwargs = dict()
        if telemetry_names:
            model_kwargs["telemetry"] = Optional[list[Literal[telemetry_names]]], Field(None, unique_items=True)
        if attribute_names:
            model_kwargs["attribute"] = Optional[list[Literal[attribute_names]]], Field(None, unique_items=True)
        for k, v in cls.child_info.items():
            model_kwargs[k] = Optional[v.cls.use_selection_model(name_prefix=name)], Field(None)
        return create_model(name, **model_kwargs)

    def all_required_paths(self, prefix=None) -> Generator[str, None, None]:
        prefix = prefix or ""
        for name, child in self.children.items():
            yield from child.all_required_paths(concat_path(prefix, name))
        for dp in self._used_data_points:
            yield concat_path(prefix, dp)

    def all_required_edges(self, self_name=None) -> Generator[tuple[str, str, str], None, None]:
        self_name = self_name or self.name
        for child_name, child in self.children.items():
            yield "is_parent_of", self_name, child_name
            yield from child.all_required_edges(child_name)
        for dp_name in self._used_data_points:
            yield "has_data_point", self_name, self.data_point_info[dp_name].__class__.__name__

    def match_data_points(self, pattern_or_uses: str | dict | Path, paths: list[str] = None) -> Iterable[str]:
        if isinstance(pattern_or_uses, str):
            return filter(partial(self.path_match, pattern_or_uses),
                          paths or self.all_required_paths())
        else:
            valid_paths = set(decouple_uses(pattern_or_uses))
            return filter(valid_paths.__contains__,
                          paths or self.all_required_paths())

    @staticmethod
    def path_match(pattern: str, path: str) -> bool:
        if pattern is not None:
            return bool(re.fullmatch(format_regex(pattern), path))
        else:
            return True

    @classmethod
    def create(cls,
               name: str,
               *entities: Union["Entity", Type["Entity"]],
               base_classes: Optional[list[str]] = None,
               asset_library_path: Optional[str] = None,
               asset_library_name: str = "tiro.assets",
               **entity_dict: dict[str, Union["Entity", Type["Entity"]]]
               ) -> Type["Entity"]:
        """Dynamically create the entity class according to the entity name defined in an asset library"""
        if base_classes:
            if asset_library_path and asset_library_path not in sys.path:
                sys.path.insert(0, asset_library_path)
            bases = []
            for base_class in base_classes:
                base_class, _, base_name = base_class.rpartition(".")
                if not base_class:
                    base = getattr(import_module(asset_library_name), base_name)
                else:
                    base = getattr(import_module(f"{asset_library_name}.{base_class}"), base_name)
                bases.append(base)
            bases = tuple(bases)
        else:
            bases = (Entity,)
        ann = {}
        for item in entities:
            if isinstance(item, type) and issubclass(item, Entity):
                item = item.many(faking_number=1)
            ann[item.cls.__name__] = item
        for k, v in entity_dict.items():
            if isinstance(v, type) and issubclass(v, Entity):
                v = v.many(faking_number=1)
            ann[k] = v
        return type(name, bases, dict(__annotations__=ann))

    @classmethod
    def create_from_define_string(cls,
                                  name: str,
                                  defs: dict,
                                  prefix: str = "",
                                  asset_library_path: Optional[str] = None,
                                  asset_library_name: str = "tiro.assets") -> EntityList:
        """Dynamically create the entity from a dictionary containing model infos"""
        if prefix:
            name = f"{prefix}_{name}"
        children = {
            k: cls.create_from_define_string(
                k, v,
                prefix=name,
                asset_library_path=asset_library_path,
                asset_library_name=asset_library_name
            )
            for k, v in defs.items() if not k.startswith(YAML_META_CHAR)
        }
        base_classes = defs[f"{YAML_META_CHAR}type"]
        if not isinstance(base_classes, list):
            base_classes = [base_classes]
        entity = cls.create(name,
                            base_classes=base_classes,
                            asset_library_path=asset_library_path,
                            asset_library_name=asset_library_name,
                            **children)
        list_args = {}
        if f"{YAML_META_CHAR}number" in defs:
            number = defs[f"{YAML_META_CHAR}number"]
            if isinstance(number, str) and "-" in number:
                min_num, max_num = number.split("-")
                list_args["faking_number"] = partial(randint, int(min_num), int(max_num))
            else:
                list_args["faking_number"] = int(number)
        else:
            list_args["faking_number"] = 1
        if f"{YAML_META_CHAR}ids" in defs:
            list_args["ids"] = defs[f"{YAML_META_CHAR}ids"]
        if f"{YAML_META_CHAR}defaults" in defs:
            entity.update_defaults(**defs[f"{YAML_META_CHAR}defaults"])
        return entity.many(**list_args)

    def to_compact(self, data):
        res = {k: {c: self.children[k].to_compact(cv)
                   for c, cv in v.items()}
               for k, v in data.items() if k in self.children}
        for dp_type in DataPointInfo.SUB_CLASS_NAMES:
            if dp_type in data:
                res |= {k: v["value"] for k, v in data[dp_type].items()}
        return res
