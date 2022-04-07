from typing import Optional, Union
from uuid import uuid1

from tiro.utils import camel_to_snake, DataPointTypes
from tiro.vocabulary import Entity, DataPointInfo, Telemetry


class MockedItem:
    def __init__(self, prototype: Entity | DataPointInfo, parent: Optional["MockedEntity"] = None):
        self.prototype = prototype
        self.parent = parent


class MockedEntity(MockedItem):
    def __init__(self, *args, **kwargs):
        super(MockedEntity, self).__init__(*args, **kwargs)
        self.children: dict[str, list[MockedEntity]] = {}
        self.uuid: Optional[str] = None

        for dp_type in DataPointInfo.SUB_CLASSES:
            setattr(self, dp_type.__name__.lower(), {})
        for k in self.prototype.data_points():
            v = self.prototype.data_point_info[k]
            dps = getattr(self, v.__class__.__name__.lower())
            k = camel_to_snake(k)
            if k not in dps:
                dps[k] = MockedDataPoint(v, parent=self)

    def generate(self, regenerate=True, include_data_points=True, change_attrs=False):
        if not self.uuid or regenerate:
            self.uuid = str(uuid1())
            self.children = {}
            for k, v in self.prototype.children.items():
                num = self.prototype.child_info[k].number_faker()
                self.children[k.lower()] = [MockedEntity(v, parent=self).generate() for _ in range(num)]
        if include_data_points:
            self.generate_data_points(change_attrs=change_attrs or regenerate)
        return self

    def dict(self, regenerate=False, include_data_points=True, change_attrs=False):
        self.generate(regenerate=regenerate,
                      include_data_points=include_data_points,
                      change_attrs=change_attrs)
        res = dict(uuid=self.uuid)
        if self.children:
            res |= dict(
                entities={k: [c.dict(regenerate=regenerate,
                                     include_data_points=include_data_points,
                                     change_attrs=change_attrs) for c in v]
                          for k, v in self.children.items()}
            )
        for dp_type in DataPointInfo.SUB_CLASSES:
            dp_type_name = dp_type.__name__.lower()
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
            dps = getattr(self, dp_type.__name__.lower())
            for v in dps.values():
                v.generate(**kwargs)

    def search_entity(self, uuid):
        if uuid == self.uuid:
            return self
        else:
            for v in self.children.values():
                for c in v:
                    entity = c.search_entity(uuid)
                    if entity:
                        return entity

    def list_entities(self) -> tuple[str, "MockedEntity"]:
        self.generate(regenerate=False, include_data_points=False)
        yield self.uuid, self
        for v in self.children.values():
            for c in v:
                yield from c.list_entities()

    def list_data_points(self) -> tuple[str, "MockedDataPoint"]:
        self.generate(regenerate=False, include_data_points=False)
        for dp_type in DataPointInfo.SUB_CLASSES:
            dps = getattr(self, dp_type.__name__.lower())
            for k, v in dps.items():
                yield f"{self.uuid}/{k}", v

    def gen_data_point(self, dp_name, change_attrs=False) -> Union[DataPointTypes]:
        self.generate(regenerate=False, include_data_points=False)
        for dp_type in DataPointInfo.SUB_CLASSES:
            dps = getattr(self, dp_type.__name__.lower())
            if dp_name in dps:
                return dps[dp_name].generate(change_attrs=change_attrs).dict()
        raise KeyError(f"Cannot find data points {dp_name} in {self.prototype.unique_name}")


class MockedDataPoint(MockedItem):
    def __init__(self, *args, **kwargs):
        super(MockedDataPoint, self).__init__(*args, **kwargs)
        self.cur_value = None

    def generate(self, change_attrs=False):
        if self.cur_value is None \
                or isinstance(self.prototype, Telemetry) \
                or change_attrs:
            self.cur_value = self.prototype.faker()
        return self

    def dict(self):
        res = dict(value=self.cur_value)
        if self.prototype.unit is not None:
            res |= dict(unit=self.prototype.unit)
        return res


class Mocker:
    def __init__(self, entity: Entity):
        self.entity: MockedEntity = MockedEntity(entity)
        self.entity_cache: Optional[dict[str, MockedEntity]] = None

    def dict(self, regenerate=False, **kwargs):
        if regenerate:
            self.entity_cache = None
        return self.entity.dict(regenerate=regenerate, **kwargs)

    def gen_data_points(self, path, change_attr=False):
        uuid, dp_name = path.split("/")
        if self.entity_cache is None:
            self.entity_cache = {k: v for k, v in self.entity.list_entities()}
        return self.entity_cache[uuid].gen_data_point(dp_name, change_attrs=change_attr)

    def list_entities(self) -> list[str]:
        return [k for k, _ in self.entity.list_entities()]

    def list_data_points(self) -> list[str]:
        return [k for k, _ in self.entity.list_data_points()]
