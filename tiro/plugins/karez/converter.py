from pathlib import Path

import yaml

from karez.config import OptionalConfigEntity
from karez.converter import ConverterBase
from tiro.core import Scenario
from tiro.core.mock import Reference
from tiro.core.utils import PATH_SEP, split_path


class TiroConverter(ConverterBase):
    def __init__(self, *args, **kwargs):
        super(TiroConverter, self).__init__(*args, **kwargs)
        self._reference = None
        self._scenario = None

    @property
    def reference(self):
        if self._reference is None:
            path = Path(self.config.reference)
            self._reference = Reference(yaml.safe_load(path.open()))
        return self._reference

    @property
    def scenario(self):
        if self._scenario is None:
            self._scenario = Scenario.from_yaml(
                Path(self.config.scenario),
                *[Path(uses) for uses in self.config.uses]
            )
        return self._scenario

    @classmethod
    def role_description(cls):
        return "Converter to format Tiro data points"

    @classmethod
    def config_entities(cls):
        yield from super(TiroConverter, cls).config_entities()
        yield OptionalConfigEntity("by", "path", "Access data by path or uuid? (path, uuid)")
        yield OptionalConfigEntity("reference", None, 'Reference file (required if by="uuid"')
        yield OptionalConfigEntity("scenario", None, 'Scenario file (required if by="uuid"')
        yield OptionalConfigEntity("uses", None, 'Uses files (required if by="uuid"')

    def convert_by_uuid(self, payload):
        uuid = payload.pop("name")
        path = self.reference.search_by_uuid(uuid)
        if path is None:
            raise ValueError(f"Cannot find uuid {uuid}")
        path, _, dp_name = path.rpartition(PATH_SEP)
        path = split_path(path)
        type_path = [path[i] for i in range(0, len(path), 2)] + [dp_name]
        dp_info = self.scenario.query_data_point_info(type_path)
        category = dp_info.__class__.__name__
        path = path + [category, dp_name]
        self.update_meta(payload, category=category.lower())
        if "result" in payload:
            payload = payload["result"]
        yield from Scenario.decompose_data(path, payload)

    def convert(self, payload):
        if self.config.by == "uuid":
            yield from self.convert_by_uuid(payload)
        else:
            yield from Scenario.decompose_data(payload["path"], payload["result"])