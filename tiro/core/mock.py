import json
import logging
from typing import Optional, Union, Type
from uuid import uuid1

from faker import Faker
from fastapi import FastAPI, HTTPException

from .utils import camel_to_snake, DataPointTypes, PATH_SEP, concat_path
from .model import Entity, DataPointInfo, Telemetry


class MockedItem:
    def __init__(self, prototype: Entity | DataPointInfo, parent: Optional["MockedEntity"] = None):
        self.prototype = prototype
        self.parent = parent


class MockedEntity(MockedItem):
    """Mock data generator for an entity class"""

    def __init__(self, entity_type: Optional[str], *args, uuid=None, **kwargs):
        super(MockedEntity, self).__init__(*args, **kwargs)
        self.children: dict[str, dict[str, MockedEntity]] = {}
        self.uuid: Optional[str] = uuid or str(uuid1())
        self.entity_type: str = entity_type
        self._initialised: bool = False
        self._path: Optional[str] = None

        for dp_type in DataPointInfo.SUB_CLASSES:
            setattr(self, camel_to_snake(dp_type.__name__), {})
        for k in self.prototype.data_points():
            v = self.prototype.data_point_info[k]
            dps = getattr(self, camel_to_snake(v.__class__.__name__))
            k = camel_to_snake(k)
            if k not in dps:
                dps[k] = MockedDataPoint(v, parent=self)

    def generate(self,
                 regenerate: bool,
                 include_data_points: bool,
                 change_attrs: bool,
                 use_default: bool) -> "MockedEntity":
        if not self._initialised or regenerate:
            self.children = {}
            for k, v in self.prototype.children.items():
                _children = {}
                entity_type = camel_to_snake(k)
                prototype = self.prototype.child_info[k]
                number = prototype.number_faker()
                if prototype.ids and number > len(prototype.ids):
                    logging.warning(
                        f"Faking number ({number})is greater the length of predefined IDs ({len(prototype.ids)}."
                        f"Only {len(prototype.ids)} instances will be generated."
                    )
                if prototype.ids:
                    uuids = prototype.ids[:number]
                else:
                    uuids = [None for _ in range(number)]
                for uuid in uuids:
                    entity = MockedEntity(entity_type=entity_type, prototype=v, parent=self, uuid=uuid)
                    _children[entity.uuid] = entity.generate(regenerate=regenerate,
                                                             include_data_points=include_data_points,
                                                             change_attrs=change_attrs,
                                                             use_default=use_default)
                self.children[entity_type] = _children
            self._initialised = True
        if include_data_points:
            self._generate_data_points(change_attrs=change_attrs or regenerate, use_default=use_default)
        return self

    def dict(self,
             regenerate,
             include_data_points,
             change_attrs,
             skip_default,
             use_default) -> dict:
        """Generate a complete tree starting from current entity"""
        self.generate(regenerate=regenerate,
                      include_data_points=include_data_points,
                      change_attrs=change_attrs,
                      use_default=use_default)
        res = {}
        if self.children:
            for k, v in self.children.items():
                _values = {}
                for uuid, c in v.items():
                    _sub_value = c.dict(regenerate=regenerate,
                                        include_data_points=include_data_points,
                                        change_attrs=change_attrs,
                                        skip_default=skip_default,
                                        use_default=use_default)
                    if _sub_value:
                        _values |= {uuid: _sub_value}
                if _values:
                    res |= {k: _values}
        for dp_type in DataPointInfo.SUB_CLASSES:
            dp_type_name = camel_to_snake(dp_type.__name__)
            dps = getattr(self, dp_type_name)
            if dps:
                if include_data_points:
                    _values = {
                        k: v.dict() for k, v in dps.items()
                        if not skip_default or v.prototype.default is None
                    }
                    if _values:
                        res |= {dp_type_name: _values}
                else:
                    res |= {dp_type_name: list(dps.keys())}
        return res

    def _generate_data_points(self, use_default, **kwargs) -> None:
        for dp_type in DataPointInfo.SUB_CLASSES:
            dps = getattr(self, camel_to_snake(dp_type.__name__))
            v: MockedDataPoint
            for v in dps.values():
                v.generate(use_default=use_default, **kwargs)

    def search_entity(self, uuid: str) -> Optional["MockedEntity"]:
        if uuid == self.uuid:
            return self
        else:
            for v in self.children.values():
                for c in v.values():
                    entity = c.search_entity(uuid)
                    if entity:
                        return entity

    @property
    def path(self) -> str:
        if self._path is None:
            if not self.parent:
                self._path = ""
            else:
                self._path = concat_path(self.parent.path, self.entity_type, self.uuid)
        return self._path

    def list_entities(self) -> tuple[str, "MockedEntity"]:
        self.generate(regenerate=False,
                      include_data_points=False,
                      change_attrs=False,
                      use_default=True)
        yield self.path, self
        for v in self.children.values():
            for c in v.values():
                yield from c.list_entities()

    def list_data_points(self, skip_default) -> tuple[str, "MockedDataPoint"]:
        self.generate(regenerate=False,
                      include_data_points=False,
                      change_attrs=False,
                      use_default=True)
        for dp_type in DataPointInfo.SUB_CLASSES:
            dp_type_name = camel_to_snake(dp_type.__name__)
            dps = getattr(self, dp_type_name)
            for k, v in dps.items():
                if not skip_default or v.prototype.default is None:
                    yield concat_path(self.path, dp_type_name, k), v
        for v in self.children.values():
            for c in v.values():
                yield from c.list_data_points(skip_default)

    def gen_data_point(self, dp_name: str, change_attrs=False, use_default=True) -> dict:
        self.generate(regenerate=False,
                      include_data_points=False,
                      change_attrs=change_attrs,
                      use_default=use_default)
        dp = None
        for dp_type in DataPointInfo.SUB_CLASSES:
            dps = getattr(self, camel_to_snake(dp_type.__name__))
            if dp_name in dps:
                dp = dps[dp_name]
                break
        if dp is None:
            raise KeyError(f"Cannot find data points {dp_name} in {self.prototype.unique_name}")
        return dp.generate(change_attrs=change_attrs, use_default=use_default).dict()

    def get_child(self, path: str) -> 'MockedEntity':
        if path:
            c_type, _, path = path.partition(PATH_SEP)
            c_uuid, _, path = path.partition(PATH_SEP)
            return self.children[c_type][c_uuid].get_child(path)
        else:
            return self


class MockedDataPoint(MockedItem):
    def __init__(self, *args, **kwargs):
        super(MockedDataPoint, self).__init__(*args, **kwargs)
        self.cur_value = None
        self.gen_timestamp = None

    def generate(self, change_attrs, use_default) -> "MockedDataPoint":
        if self.cur_value is None \
                or isinstance(self.prototype, Telemetry) \
                or change_attrs:
            if use_default and self.prototype.default is not None:
                self.cur_value = self.prototype.default
            else:
                self.cur_value = self.prototype.faker()
            self.gen_timestamp = Faker().past_datetime(-self.prototype.time_var).isoformat()
        return self

    def dict(self) -> dict:
        res = dict(value=self.cur_value, timestamp=self.gen_timestamp)
        if self.prototype.unit is not None:
            res |= dict(unit=self.prototype.unit)
        return res


class Mocker:
    def __init__(self, entity: Optional[Entity] = None):
        self.entity: MockedEntity = MockedEntity(None, entity)
        self.entity_cache: Optional[dict[str, MockedEntity]] = None

    def dict(self,
             regenerate: bool = False,
             include_data_points: bool = True,
             change_attrs: bool = False,
             skip_default: bool = True,
             use_default: bool = True
             ) -> dict:
        """Generate a complete dictionary for the tree starting from the given entity."""
        if regenerate:
            self.entity_cache = None
        return self.entity.dict(regenerate=regenerate,
                                include_data_points=include_data_points,
                                change_attrs=change_attrs,
                                skip_default=skip_default,
                                use_default=use_default)

    def json(self,
             regenerate: bool = False,
             include_data_points: bool = True,
             change_attrs: bool = False,
             skip_default: bool = True,
             use_default: bool = True,
             **kwargs) -> str:
        """Generate a complete dictionary for the tree starting from the entity and return the coded json string."""
        d = self.dict(regenerate=regenerate,
                      include_data_points=include_data_points,
                      change_attrs=change_attrs,
                      skip_default=skip_default,
                      use_default=use_default)
        return json.dumps(d, **kwargs)

    def gen_data_point(self, path: str,
                       change_attr: bool = False,
                       use_default: bool = True) -> dict:
        path, _, dp_name = path.rpartition(PATH_SEP)
        path, _, _ = path.rpartition(PATH_SEP)
        return self.entity.get_child(path).gen_data_point(dp_name,
                                                          change_attrs=change_attr,
                                                          use_default=use_default)

    def list_entities(self) -> list[str]:
        return [k for k, _ in self.entity.list_entities()]

    def list_data_points(self, skip_default=True) -> list[str]:
        return [k for k, _ in self.entity.list_data_points(skip_default=skip_default)]


class MockApp(FastAPI):
    def __init__(self, mocker: Mocker, *args, skip_default: bool = True, use_default: bool=True, **kwargs):
        super(MockApp, self).__init__(*args, **kwargs)
        self.mocker: Mocker = mocker
        self.skip_default: bool = skip_default
        self.use_default: bool = use_default

        @self.get("/hierarchy")
        def get_hierarchy():
            return self.mocker.dict(include_data_points=False)

        @self.get("/sample")
        def get_sample(change_attrs: bool = False):
            return self.mocker.dict(change_attrs=change_attrs)

        @self.get("/points/")
        def list_points():
            return self.mocker.list_data_points(skip_default=self.skip_default)

        @self.get("/points/{path:str}")
        def get_point(path):
            try:
                return self.mocker.gen_data_point(path, use_default=self.use_default)
            except KeyError as e:
                raise HTTPException(status_code=404, detail=str(e))
