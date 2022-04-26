import re
import sys
from collections.abc import Iterable
from copy import copy
from datetime import datetime, timedelta
from functools import partial
from importlib import import_module
from inspect import get_annotations
from pathlib import Path
from random import randint
from typing import TypeVar, Generic, Optional, Type, Any, Union, Callable, Literal

from pydantic import BaseModel, create_model, Field
from pydantic.generics import GenericModel
from yaml import safe_load

from .utils import camel_to_snake, DataPointTypes, PATH_SEP, concat_path, YAML_META_CHAR

DPT = TypeVar("DPT", *DataPointTypes)


class DataPointInfo:
    SUB_CLASSES = []

    def __init__(self,
                 type: Any,
                 unit: Optional[str] = None,
                 faker: Optional[Callable] = None,
                 time_var: Optional[timedelta] = timedelta(seconds=0)):
        self.type = type
        self.unit = unit
        self.faker = faker
        self.time_var = time_var

    def __init_subclass__(cls, **kwargs):
        cls.SUB_CLASSES.append(cls)


class Telemetry(DataPointInfo):
    """Data point that dynamically changes."""
    pass


class Attribute(DataPointInfo):
    """Data point that seldom changes"""
    pass


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
        super().__init_subclass__(**kwargs)
        cls.data_point_info = copy(cls.data_point_info)
        cls.child_info: dict[str, EntityList] = {}
        for k, v in get_annotations(cls).items():
            if isinstance(v, DataPointInfo):
                cls.data_point_info[k] = v
                if hasattr(cls, k):
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

    def _parse_use_yaml(self, d, prefix="") -> Iterable[str]:
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
                elif path in self.child_info:
                    if path not in self.children:
                        self.children[path] = self.child_info[path].new_entity(self)
        return self

    def _create_date_points_model(self, dp_type: Type[DataPoint]) -> Optional[Type[BaseModel]]:
        """Dynamically generate Pydantic model for all data points in the entity."""
        info = {k: v for k, v in self.data_point_info.items()
                if isinstance(v, dp_type) and k in self._used_data_points}
        if not info:
            return None
        sub_models: dict[str, tuple[type, Any]] = {}
        for dp_name, dp_info in info.items():
            dp_model_name = f"{self.name}_{dp_name}"
            model_cache = self.__class__.cached_data_point_model
            if dp_model_name not in model_cache:
                model_cache[dp_model_name] = type(f"{self.name}_{dp_name}",
                                                  (DataPoint[dp_info.type],),
                                                  dict(_unit=dp_info.unit))
            sub_models[camel_to_snake(dp_name)] = (model_cache[dp_model_name], ...)
        return create_model(f"{self.unique_name}_{dp_type.__name__}", **sub_models)

    def _create_entities_model(self,
                               hide_data_points: bool = False
                               ) -> dict[str, tuple[type, Any]]:
        """Dynamically generate Pydantic model for the entity type."""
        fields = {
            camel_to_snake(name): (
                Optional[
                    ins.model_list(self.child_info[name], hide_data_points=hide_data_points)
                ], ...)
            for name, ins in self.children.items()
        }
        return fields

    def model_list(self, entity_list, hide_data_points: bool = False) -> Type[dict[str, BaseModel]]:
        """Return a type representing a dict of entities"""
        if entity_list.ids:
            str_type = Literal[tuple(entity_list.ids)]
        else:
            str_type = str
        return dict[str_type, self.model(hide_data_points=hide_data_points)]

    def model(self, hide_data_points: bool = False) -> Type[BaseModel]:
        """Generate a complete Pydantic model for a model tree staring from current entity."""
        fields: dict[str, tuple[type, Any]] = self._create_entities_model(hide_data_points=hide_data_points)
        if not hide_data_points:
            for dp_type in DataPointInfo.SUB_CLASSES:
                dp_model = self._create_date_points_model(dp_type)
                if dp_model:
                    fields |= {camel_to_snake(dp_type.__name__): (dp_model, ...)}
        return create_model(self.unique_name, config=self.Config, **fields)

    def __getattr__(self, item: str) -> RequireHelper:
        return RequireHelper(item, self)

    def data_points(self, used_only: bool = True) -> list[str]:
        if used_only:
            return list(self._used_data_points)
        else:
            return list(self.data_point_info.keys())

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
        # children = tuple(v.cls.use_selection_model(name_prefix=name) for v in cls.child_info.values())
        # if children:
        #     model_kwargs["children"] = Optional[list[Union[children]]], Field(...)
        return create_model(name, **model_kwargs)

    def all_required_paths(self, prefix=None) -> Iterable[str]:
        prefix = prefix or ""
        for name, child in self.children.items():
            yield from child.all_required_paths(concat_path(prefix, name))
        for dp in self._used_data_points:
            yield concat_path(prefix, dp)

    def all_required_edges(self, self_name=None) -> Iterable[tuple[str, str, str]]:
        self_name = self_name or self.name
        for child_name, child in self.children.items():
            yield "is_parent_of", self_name, child_name
            yield from child.all_required_edges(child_name)
        for dp_name in self._used_data_points:
            yield "has_data_point", self_name, self.data_point_info[dp_name].__class__.__name__

    def match_data_points(self, pattern: str) -> Iterable[str]:
        pattern = pattern.replace("%", "\.")
        for path in self.all_required_paths():
            if re.fullmatch(pattern, path):
                yield path

    @classmethod
    def create(cls,
               name: str,
               *entities: Union["Entity", Type["Entity"]],
               base_class: Optional[str] = None,
               asset_library_path: Optional[str] = None,
               asset_library_name: str = "tiro.assets",
               **entity_dict: dict[str, Union["Entity", Type["Entity"]]]
               ) -> Type["Entity"]:
        """Dynamically create the entity class according to the entity name defined in an asset library"""
        if base_class:
            if asset_library_path and asset_library_path not in sys.path:
                sys.path.insert(0, asset_library_path)
            base_class, _, base_name = base_class.rpartition(".")
            if not base_class:
                base = getattr(import_module(asset_library_name), base_name)
            else:
                base = getattr(import_module(f"{asset_library_name}.{base_class}"), base_name)
        else:
            base = Entity
        ann = {}
        for item in entities:
            if isinstance(item, type) and issubclass(item, Entity):
                item = item.many(faking_number=1)
            ann[item.cls.__name__] = item
        for k, v in entity_dict.items():
            if isinstance(v, type) and issubclass(v, Entity):
                v = v.many(faking_number=1)
            ann[k] = v
        return type(name, (base,), dict(__annotations__=ann))

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
        entity = cls.create(name,
                            base_class=defs[f"{YAML_META_CHAR}type"],
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
        return entity.many(**list_args)
