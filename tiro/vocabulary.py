from inspect import get_annotations
from typing import TypeVar, Generic, Optional, Type, Any, Union, Callable

from pydantic import BaseModel, conlist, create_model
from pydantic.generics import GenericModel

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
        return self.cls(parent, min_items=self.min_items, max_items=self.max_items)


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

    def use(self):
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
                 min_items: Optional[int] = None,
                 max_items: Optional[int] = None):
        self.children: dict[str, Entity] = {}
        self.parent: Optional[Entity] = parent
        self.conlist_args: dict[str, Any] = dict(
            min_items=min_items,
            max_items=max_items,
            unique_items=True
        )
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

    def requires(self, *paths: str) -> "Entity":
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

    def _create_date_points_model(self, dp_type) -> Optional[BaseModel]:
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

    def _create_entities_model(self, hide_data_points: bool = False) -> Optional[BaseModel]:
        fields = {
            name.lower(): (ins.model_list(hide_data_points=hide_data_points), ...)
            for name, ins in self.children.items()
        }
        if fields:
            return create_model(f"{self.unique_name}_Entities", **fields)
        else:
            return None

    def model_list(self, hide_data_points: bool = False):
        return conlist(self.model(hide_data_points=hide_data_points), **self.conlist_args)

    def model(self, hide_data_points: bool = False) -> Type[BaseModel]:
        fields: dict[str, tuple[type, Any]] = dict(
            uuid=(str, ...)
        )
        entities_model = self._create_entities_model(hide_data_points=hide_data_points)
        if entities_model:
            fields |= dict(entities=(entities_model, ...))
        if not hide_data_points:
            for dp_type in DataPointInfo.SUB_CLASSES:
                dp_model = self._create_date_points_model(dp_type)
                if dp_model:
                    fields |= {dp_type.__name__.lower(): (dp_model, ...)}
        return create_model(self.unique_name, __config__=self.Config, **fields)

    def __getattr__(self, item):
        return RequireHelper(item, self)

    def fake(self, include_data_points=True) -> "Entity":
        from pydantic_factories import ModelFactory
        return type("_Factory",
                    (ModelFactory,),
                    dict(__model__=self.model(hide_data_points=not include_data_points))
                    ).build()

    def data_points(self, used_only: bool = True) -> list[str]:
        if used_only:
            return list(self._used_data_points)
        else:
            return list(self.data_point_info.keys())
