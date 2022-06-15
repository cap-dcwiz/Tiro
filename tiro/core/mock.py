import json
import logging
import re
from pathlib import Path
from random import uniform
from typing import Optional, Generator

import yaml
from faker import Faker
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .utils import camel_to_snake, PATH_SEP, concat_path, split_path
from .model import Entity, DataPointInfo, Telemetry


class Reference:
    def __init__(self, reference=None):
        reference = reference or {}
        self.tree = reference.get("tree", None)
        self.value_range = reference.get("value_range", None)
        self.uuid_map = reference.get("uuid_map", None)

    def get_children(self, path, tree=None):
        if self.tree:
            if tree is None:
                tree = self.tree
            path = split_path(path)
            if path:
                component = path.pop(0)
                if component in tree:
                    return self.get_children(path, tree[component])
                return {}
            else:
                return tree

    def get_data_points(self, path):
        item = self.get_children(path)
        if item is None:
            return None
        else:
            return item.get("DataPoints", {})

    def search_by_uuid(self, uuid):
        if self.uuid_map is not None:
            return self.uuid_map.get(uuid, None)
        return None

    def list_uuids(self):
        if self.uuid_map:
            return list(self.uuid_map.keys())
        else:
            return []

    def get_value_range(self, path, name):
        if self.value_range:
            path = split_path(path)
            path = [path[i] for i in range(0, len(path), 2)]
            path.append(name)
            return self.value_range.get(PATH_SEP.join(path), None)


class MockedItem:
    _name_count = {}

    def __init__(self,
                 prototype: Entity | DataPointInfo,
                 reference: Reference,
                 parent: Optional["MockedEntity"] = None
                 ):
        self.prototype = prototype
        self.reference = reference
        self.parent = parent

    def gen_uuid(self):
        name = self.prototype.__class__.__name__.split('_')[-1]
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
        if name not in MockedItem._name_count:
            MockedItem._name_count[name] = 0
        no = MockedItem._name_count[name]
        uuid = f"{name}_{no}"
        MockedItem._name_count[name] += 1
        return uuid


class MockedEntity(MockedItem):
    """Mock data generator for an entity class"""

    def __init__(self, entity_type: Optional[str], *args, uuid=None, **kwargs):
        super(MockedEntity, self).__init__(*args, **kwargs)
        self.children: dict[str, dict[str, MockedEntity]] = {}
        # self.uuid: Optional[str] = uuid or str(uuid1())
        self.uuid: Optional[str] = uuid or self.gen_uuid()
        self.entity_type: str = entity_type
        self._initialised: bool = False
        self._path: Optional[str] = None

        for dp_type in DataPointInfo.SUB_CLASSES:
            setattr(self, camel_to_snake(dp_type.__name__), {})

        ref_dps = self.reference.get_data_points(self.path)
        if ref_dps is not None:
            ref_dps = set(ref_dps)

        for k in self.prototype.data_points():
            v = self.prototype.data_point_info[k]
            dps = getattr(self, camel_to_snake(v.__class__.__name__))
            k = camel_to_snake(k)
            if ref_dps is None or k in ref_dps and k not in dps:
                dps[k] = MockedDataPoint(prototype=v, name=k, parent=self, reference=self.reference)

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
                child_path = f"{self.path}{PATH_SEP}{entity_type}" if self.path else entity_type
                uuids = self.reference.get_children(child_path)
                if uuids is None:
                    if prototype.ids:
                        uuids = prototype.ids
                    else:
                        uuids = [None for _ in range(number)]
                else:
                    uuids = list(uuids.keys())
                    number = len(uuids)
                for uuid in uuids[:number]:
                    entity = MockedEntity(entity_type=entity_type,
                                          prototype=v,
                                          parent=self,
                                          reference=self.reference,
                                          uuid=uuid)
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

    def list_entities(self) -> Generator[tuple[str, "MockedEntity"]]:
        self.generate(regenerate=False,
                      include_data_points=False,
                      change_attrs=False,
                      use_default=True)
        yield self.path, self
        for v in self.children.values():
            for c in v.values():
                yield from c.list_entities()

    def list_data_points(self, skip_default) -> Generator[tuple[str, "MockedDataPoint"]]:
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
    _faker = Faker()

    def __init__(self, name, *args, **kwargs):
        super(MockedDataPoint, self).__init__(*args, **kwargs)
        self.cur_value = None
        self.gen_timestamp = None
        self.name = name

    def generate(self, change_attrs, use_default) -> "MockedDataPoint":
        if self.cur_value is None \
                or isinstance(self.prototype, Telemetry) \
                or change_attrs:
            if use_default and self.prototype.default is not None:
                self.cur_value = self.prototype.default
            else:
                value_range = self.reference.get_value_range(self.parent.path, self.name)
                if value_range is not None:
                    self.cur_value = uniform(value_range["min"], value_range["max"])

                    # pyfloat bug!
                    # self.cur_value = self._faker.pyfloat(min_value=value_range["min"],
                    #                                      max_value=value_range["max"])
                else:
                    self.cur_value = self.prototype.faker()
                    if isinstance(self.cur_value, BaseModel):
                        self.cur_value = self.cur_value.dict()
            self.gen_timestamp = self._faker.past_datetime(-self.prototype.time_var).isoformat()
        return self

    def dict(self) -> dict:
        res = dict(value=self.cur_value, timestamp=self.gen_timestamp)
        if self.prototype.unit is not None:
            res |= dict(unit=self.prototype.unit)
        return res


class Mocker:
    def __init__(self,
                 entity: Optional[Entity] = None,
                 reference: Optional[Path | dict] = None):
        if isinstance(reference, Path):
            reference = yaml.safe_load(reference.open())
        self.entity: MockedEntity = MockedEntity(entity_type=None,
                                                 prototype=entity,
                                                 reference=Reference(reference))
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
        self.entity.generate(regenerate=False,
                             include_data_points=False,
                             change_attrs=change_attr,
                             use_default=use_default)
        path, _, dp_name = path.rpartition(PATH_SEP)
        path, _, _ = path.rpartition(PATH_SEP)
        return self.entity.get_child(path).gen_data_point(dp_name,
                                                          change_attrs=change_attr,
                                                          use_default=use_default)

    def gen_value_by_uuid(self,
                          uuid: str,
                          change_attr: bool = False,
                          use_default: bool = True,
                          value_only: bool = False) -> dict:
        self.entity.generate(regenerate=False,
                             include_data_points=False,
                             change_attrs=change_attr,
                             use_default=use_default)
        path = self.entity.reference.search_by_uuid(uuid)
        if path is not None:
            path, _, dp_name = path.rpartition(PATH_SEP)
            dp = self.entity.get_child(path).gen_data_point(dp_name,
                                                            change_attrs=change_attr,
                                                            use_default=use_default)
            if value_only:
                return dp["value"]
            else:
                return dp
        else:
            raise KeyError

    def list_entities(self) -> list[str]:
        return [k for k, _ in self.entity.list_entities()]

    def list_data_points(self, skip_default=True) -> list[str]:
        return [k for k, _ in self.entity.list_data_points(skip_default=skip_default)]

    def list_uuids(self) -> list[str]:
        return self.entity.reference.list_uuids()


class MockApp(FastAPI):
    def __init__(self,
                 mocker: Mocker,
                 *args,
                 skip_defaults: bool = True,
                 use_defaults: bool = True,
                 **kwargs):
        super(MockApp, self).__init__(*args, **kwargs)
        self.mocker: Mocker = mocker
        self.skip_defaults: bool = skip_defaults
        self.use_defaults: bool = use_defaults

        @self.get("/hierarchy")
        def get_hierarchy():
            return self.mocker.dict(include_data_points=False)

        @self.get("/sample")
        def get_sample(change_attrs: bool = False):
            return self.mocker.dict(change_attrs=change_attrs)

        @self.get("/points/")
        def list_points():
            return self.mocker.list_data_points(skip_default=self.skip_defaults)

        @self.get("/values/")
        def list_uuids():
            return self.mocker.list_uuids()

        @self.get("/points/{path:str}")
        def get_point(path):
            try:
                return self.mocker.gen_data_point(path, use_default=self.use_defaults)
            except KeyError as e:
                raise HTTPException(status_code=404,
                                    detail=f"Cannot find path {path}"
                                    ) from e

        @self.get("/values/{uuid:str}")
        def get_value_by_uuid(uuid):
            try:
                return self.mocker.gen_value_by_uuid(uuid,
                                                     use_default=self.use_defaults,
                                                     value_only=True)
            except KeyError as e:
                logging.error(f"{type(e)}:{e}")
                raise HTTPException(status_code=404,
                                    detail=f"Cannot find uuid {uuid}"
                                    ) from e
