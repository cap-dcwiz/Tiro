from functools import partial
from inspect import get_annotations
from typing import TypeVar, Generic, Optional, Type, Any

from pydantic import BaseModel, conlist, create_model
from pydantic.generics import GenericModel

from .utils import camel_to_snake

DPT = TypeVar("DPT", int, float, str)


class DataPointInfo:
    SUB_CLASSES = []

    def __init__(self, type: Any, unit: Optional[str] = None):
        self.type = type
        self.unit = unit

    def __init_subclass__(cls, **kwargs):
        cls.SUB_CLASSES.append(cls)


class Telemetry(DataPointInfo):
    pass


class Attribute(DataPointInfo):
    pass


class DataPoint(GenericModel, Generic[DPT]):
    value: DPT
    _unit: Optional[str] = None

    class Config:
        @staticmethod
        def schema_extra(schema: dict[str, Any], model: Type["DataPoint"]) -> None:
            schema["unit"] = model._unit
            for p in schema["properties"].values():
                p.pop("title", None)


class Entity:
    class Config:
        @staticmethod
        def schema_extra(schema: dict[str, Any], model: Type["Entity"]) -> None:
            schema.pop("title", None)
            for p in schema["properties"].values():
                p.pop("title", None)

    def __init_subclass__(cls, **kwargs):
        cls.data_points: dict[str, DataPointInfo] = {}
        for k, v in get_annotations(cls).items():
            if isinstance(v, DataPointInfo):
                cls.data_points[k] = v
        cls.cached_data_point_model = {}

    def __init__(self, *children, min_items: Optional[int] = None, max_items: Optional[int] = None):
        self.children: list[Entity | Type[Entity]] = []
        for c in children:
            if isinstance(c, type):
                c = c()
            c.parent = self
            self.children.append(c)
        self.parent: Optional[Entity] = None
        self.conlist_args: dict[str, Any] = dict(
            min_items=min_items,
            max_items=max_items,
            unique_items=True
        )
        self._used_data_points = set()

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def unique_name(self) -> str:
        if self.parent:
            return f"{self.parent.unique_name}_{self.__class__.__name__}"
        else:
            return self.name

    def use(self, name: str) -> "Entity":
        if name in self.data_points:
            self._used_data_points.add(name)
        return self

    def _create_date_point_set(self, dp_type) -> Optional[BaseModel]:
        info = {k: v for k, v in self.data_points.items()
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

    def model(self, hide_data_points: bool = False) -> Type[BaseModel]:
        fields: dict[str, tuple[type, Any]] = dict(
            name=(str, ...)
        )
        fields |= {
            c.name.lower(): (conlist(c.model(hide_data_points=hide_data_points), **c.conlist_args), ...)
            for c in self.children
        }
        if not hide_data_points:
            for dp_type in DataPointInfo.SUB_CLASSES:
                dp_model = self._create_date_point_set(dp_type)
                if dp_model:
                    fields |= {dp_type.__name__.lower(): (dp_model, ...)}
        return create_model(self.unique_name, __config__=self.Config, **fields)

    def __getattr__(self, item):
        for c in self.children:
            if c.name == item:
                return c
        if item in self.data_points:
            return type("_helper", (), dict(use=staticmethod(partial(self.use, item))))
        raise AttributeError(item)

    def fake(self, include_data_points=True) -> "Entity":
        from pydantic_factories import ModelFactory
        return type("_Factory",
                    (ModelFactory,),
                    dict(__model__=self.model(hide_data_points=not include_data_points))
                    ).build()
