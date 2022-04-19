import json
from datetime import datetime
from typing import Optional, Union
from uuid import uuid1

from faker import Faker
from fastapi import FastAPI, HTTPException

from tiro.utils import camel_to_snake, DataPointTypes, PATH_SEP, concat_path
from tiro.model import Entity, DataPointInfo, Telemetry


class MockedItem:
    def __init__(self, prototype: Entity | DataPointInfo, parent: Optional["MockedEntity"] = None):
        self.prototype = prototype
        self.parent = parent


class MockedEntity(MockedItem):
    def __init__(self, entity_type, *args, **kwargs):
        super(MockedEntity, self).__init__(*args, **kwargs)
        self.children: dict[str, dict[str, MockedEntity]] = {}
        self.uuid: Optional[str] = str(uuid1())
        self.entity_type = entity_type
        self._initialised = False
        self._path = None

        for dp_type in DataPointInfo.SUB_CLASSES:
            setattr(self, camel_to_snake(dp_type.__name__), {})
        for k in self.prototype.data_points():
            v = self.prototype.data_point_info[k]
            dps = getattr(self, camel_to_snake(v.__class__.__name__))
            k = camel_to_snake(k)
            if k not in dps:
                dps[k] = MockedDataPoint(v, parent=self)

    def generate(self,
                 regenerate=True,
                 include_data_points=True,
                 change_attrs=False) -> "MockedEntity":
        if not self._initialised or regenerate:
            self.children = {}
            for k, v in self.prototype.children.items():
                num = self.prototype.child_info[k].number_faker()
                entity_type = camel_to_snake(k)
                _children = {}
                for _ in range(num):
                    entity = MockedEntity(entity_type=entity_type, prototype=v, parent=self)
                    _children[entity.uuid] = entity.generate()
                self.children[entity_type] = _children
            self._initialised = True
        if include_data_points:
            self.generate_data_points(change_attrs=change_attrs or regenerate)
        return self

    def dict(self,
             regenerate=False,
             include_data_points=True,
             change_attrs=False) -> dict:
        self.generate(regenerate=regenerate,
                      include_data_points=include_data_points,
                      change_attrs=change_attrs)
        res = {}
        if self.children:
            res |= {k: {uuid: c.dict(regenerate=regenerate,
                                     include_data_points=include_data_points,
                                     change_attrs=change_attrs) for uuid, c in v.items()}
                    for k, v in self.children.items()}
        for dp_type in DataPointInfo.SUB_CLASSES:
            dp_type_name = camel_to_snake(dp_type.__name__)
            dps = getattr(self, dp_type_name)
            if dps:
                if include_data_points:
                    res |= {
                        dp_type_name: {
                            k: v.dict() for k, v in dps.items()
                        }
                    }
                else:
                    res |= {dp_type_name: list(dps.keys())}
        return res

    def generate_data_points(self, **kwargs):
        for dp_type in DataPointInfo.SUB_CLASSES:
            dps = getattr(self, camel_to_snake(dp_type.__name__))
            for v in dps.values():
                v.generate(**kwargs)

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
        self.generate(regenerate=False, include_data_points=False)
        yield self.path, self
        for v in self.children.values():
            for c in v.values():
                yield from c.list_entities()

    def list_data_points(self) -> tuple[str, "MockedDataPoint"]:
        self.generate(regenerate=False, include_data_points=False)
        for dp_type in DataPointInfo.SUB_CLASSES:
            dp_type_name = camel_to_snake(dp_type.__name__)
            dps = getattr(self, dp_type_name)
            for k, v in dps.items():
                yield concat_path(self.path, dp_type_name, k), v
        for v in self.children.values():
            for c in v.values():
                yield from c.list_data_points()

    def gen_data_point(self, dp_name: str, change_attrs=False) -> Union[DataPointTypes]:
        self.generate(regenerate=False, include_data_points=False)
        for dp_type in DataPointInfo.SUB_CLASSES:
            dps = getattr(self, camel_to_snake(dp_type.__name__))
            if dp_name in dps:
                return dps[dp_name].generate(change_attrs=change_attrs).dict()
        raise KeyError(f"Cannot find data points {dp_name} in {self.prototype.unique_name}")

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

    def generate(self, change_attrs=False) -> "MockedDataPoint":
        if self.cur_value is None \
                or isinstance(self.prototype, Telemetry) \
                or change_attrs:
            self.cur_value = self.prototype.faker()
            self.gen_timestamp = Faker().past_datetime(-self.prototype.time_var).isoformat()
        return self

    def dict(self) -> dict:
        res = dict(value=self.cur_value, timestamp=self.gen_timestamp)
        if self.prototype.unit is not None:
            res |= dict(unit=self.prototype.unit)
        return res


class Mocker:
    def __init__(self, entity: Entity):
        self.entity: MockedEntity = MockedEntity(None, entity)
        self.entity_cache: Optional[dict[str, MockedEntity]] = None

    def dict(self, regenerate: bool = False, **kwargs) -> dict:
        if regenerate:
            self.entity_cache = None
        return self.entity.dict(regenerate=regenerate, **kwargs)

    def json(self,
             regenerate: bool = False,
             include_data_points=True,
             change_attrs=False, **kwargs) -> str:
        d = self.dict(regenerate=regenerate,
                      include_data_points=include_data_points,
                      change_attrs=change_attrs)
        return json.dumps(d, **kwargs)

    def gen_data_point(self, path: str, change_attr: bool = False):
        path, _, dp_name = path.rpartition(PATH_SEP)
        path, _, _ = path.rpartition(PATH_SEP)
        return self.entity.get_child(path).gen_data_point(dp_name, change_attrs=change_attr)

    def list_entities(self) -> list[str]:
        return [k for k, _ in self.entity.list_entities()]

    def list_data_points(self) -> list[str]:
        return [k for k, _ in self.entity.list_data_points()]


class MockApp(FastAPI):
    def __init__(self, entity: Entity, *args, **kwargs):
        super(MockApp, self).__init__(*args, **kwargs)
        self.mocker: Mocker = Mocker(entity)

        @self.get("/hierarchy")
        def get_hierarchy():
            return self.mocker.dict(include_data_points=False)

        @self.get("/sample")
        def get_sample(change_attrs: bool = False):
            return self.mocker.dict(change_attrs=change_attrs)

        @self.get("/points/")
        def list_points():
            return self.mocker.list_data_points()

        @self.get("/points/{path:str}")
        def get_point(path):
            try:
                return self.mocker.gen_data_point(path)
            except KeyError as e:
                raise HTTPException(status_code=404, detail=str(e))
