from pathlib import Path

import yaml

from karez.config import OptionalConfigEntity
from tiro.core import Scenario
from tiro.core.mock import Reference
from tiro.core.utils import PATH_SEP, split_path
from karez.converter.extras.fix_timestamp import Converter as FixTimestampConverter


class TiroUpdateInfoForValueConverter(FixTimestampConverter):
    def __init__(self, *args, **kwargs):
        super(TiroUpdateInfoForValueConverter, self).__init__(*args, **kwargs)
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
            scenario_file = Path(self.config.scenario)
            if isinstance(self.config.uses, list):
                uses = [Path(uses) for uses in self.config.uses]
            else:
                uses = Path(self.config.uses)
            self._scenario = Scenario.from_yaml(scenario_file, uses)
        return self._scenario

    @classmethod
    def role_description(cls):
        return "Converter to update information for value fetched by uuids"

    @classmethod
    def config_entities(cls):
        yield from super(TiroUpdateInfoForValueConverter, cls).config_entities()
        yield OptionalConfigEntity("reference", None, 'Reference file (required if by="uuid"')
        yield OptionalConfigEntity("scenario", None, 'Scenario file (required if by="uuid"')
        yield OptionalConfigEntity("uses", None, 'Uses files (required if by="uuid"')

    def convert(self, payload):
        if self.is_configured("tz_infos"):
            payload = list(FixTimestampConverter.convert(self, payload))[0]
        uuid = payload.pop("name")
        path = self.reference.search_by_uuid(uuid)
        if path is None:
            raise ValueError(f"Cannot find uuid {uuid}")
        path, _, dp_name = path.rpartition(PATH_SEP)
        path = split_path(path)
        type_path = [path[i] for i in range(0, len(path), 2)] + [dp_name]
        dp_info = self.scenario.query_data_point_info(type_path)
        category = dp_info.__class__.__name__
        path = PATH_SEP.join(path + [category, dp_name])
        result = dict(path=path, result=payload)
        self.copy_meta(result, payload, clear_old=True)
        self.update_meta(result, category=category.lower())
        yield result


class TiroPreprocessConverter(FixTimestampConverter):
    @classmethod
    def role_description(cls):
        return "Converter to preprocess data points before send to data lake"

    def convert(self, payload):
        if self.is_configured("tz_infos"):
            for item in Scenario.decompose_data(payload["path"], payload["result"]):
                yield from FixTimestampConverter.convert(self, item)
        else:
            yield from Scenario.decompose_data(payload["path"], payload["result"])
