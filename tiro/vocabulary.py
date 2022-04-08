from collections.abc import Iterable
from inspect import get_annotations
from typing import TypeVar, Generic, Optional, Type, Any, Union, Callable

from pydantic import BaseModel, create_model
from pydantic.generics import GenericModel
from yaml import safe_load

from .utils import camel_to_snake, DataPointTypes

DPT = TypeVar("DPT", *DataPointTypes)


class DataPointInfo:
    SUB_CLASSES = []

    def __init__(self,
                 type: Any,
                 unit: Optional[str] = None,
                 faker: Optional[Callable] = None):
        self.type = type
        self.unit = unit
        self.faker = faker

    def __init_subclass__(cls, **kwargs):
        cls.SUB_CLASSES.append(cls)


class Telemetry(DataPointInfo):
    pass


class Attribute(DataPointInfo):
    pass


class EntityList:
    def __init__(self,
                 cls: Type["Entity"],
                 min_items: Optional[int] = None,
                 max_items: Optional[int] = None,
                 faking_number: Optional[Callable | int] = None):
        self.cls = cls
        self.min_items = min_items
        self.max_items = max_items
        if isinstance(faking_number, int):
            self.number_faker = lambda: faking_number
        else:
            self.number_faker = faking_number

    def new_entity(self, parent: Optional["Entity"] = None):
        # return self.cls(parent, min_items=self.min_items, max_items=self.max_items)
        return self.cls(parent)


class DataPoint(GenericModel, Generic[DPT]):
    value: DPT
    _unit: Optional[str] = None

    class Config:
        @staticmethod
        def schema_extra(schema: dict[str, Any], model: Type["DataPoint"]) -> None:
            schema["unit"] = model._unit
            for p in schema["properties"].values():
                p.pop("title", None)


class RequireHelper:
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

    def __init_subclass__(cls, **kwargs):
        cls.data_point_info: dict[str, DataPointInfo] = {}
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

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def unique_name(self) -> str:
        if self.parent:
            return f"{self.parent.unique_name}_{self.__class__.__name__}"
        else:
            return self.name

    def _parse_yaml(self, d, prefix="") -> Iterable[str]:
        if isinstance(d, list):
            for item in d:
                yield from self._parse_yaml(item, prefix=prefix)
        elif isinstance(d, dict):
            for k, v in d.items():
                yield from self._parse_yaml(v, prefix=f"{prefix}.{k}")
        elif isinstance(d, str):
            yield f"{prefix}.{d}".strip(".")

    def requires(self, *paths: str, yaml: str = None) -> "Entity":
        paths = list(paths)
        if yaml:
            paths.extend(self._parse_yaml(safe_load(yaml)))
        for path in paths:
            if "." in path:
                entity, _, path = path.partition(".")
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
        fields = {
            name.lower(): (Optional[ins.model_list(hide_data_points=hide_data_points)], ...)
            for name, ins in self.children.items()
        }
        return fields

    def model_list(self, hide_data_points: bool = False) -> Type[dict[str, BaseModel]]:
        return dict[str, self.model(hide_data_points=hide_data_points)]

    def model(self, hide_data_points: bool = False) -> Type[BaseModel]:
        fields: dict[str, tuple[type, Any]] = self._create_entities_model(hide_data_points=hide_data_points)
        if not hide_data_points:
            for dp_type in DataPointInfo.SUB_CLASSES:
                dp_model = self._create_date_points_model(dp_type)
                if dp_model:
                    fields |= {dp_type.__name__.lower(): (dp_model, ...)}
        return create_model(self.unique_name, config=self.Config, **fields)

    def __getattr__(self, item: str) -> RequireHelper:
        return RequireHelper(item, self)

    def data_points(self, used_only: bool = True) -> list[str]:
        if used_only:
            return list(self._used_data_points)
        else:
            return list(self.data_point_info.keys())
