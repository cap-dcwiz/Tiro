import os

import json
from collections import namedtuple
import pandas as pd
import numpy as np
import yaml
from loguru import logger as logging

from tiro.core.draft import DraftGenerator

Point = namedtuple("Point", "min max")


class Asset:
    def __init__(self, asset_type, name):
        self.asset_type = asset_type
        self.name = name
        self.children = []
        self.points = {}

    def add_child(self, asset):
        self.children.append(asset)
        return asset

    def add_asset(self, asset_type, name):
        return self.add_child(Asset(asset_type, name))

    def add_point(self, point_name, min, max):
        point = Point(min, max)
        self.points[point_name] = point

    def add_point_to_children(self, path, point_name, min, max):
        """
        Add a point to all children with the given path.
        For example, if the path is ["Rack", "Server"], then the point will be added to all servers.
        """
        for child in self[path].values():
            child.add_point(point_name, min, max)

    def __str__(self):
        return f"{self.asset_type}#{self.name}"

    def __setattr__(self, key, value):
        if isinstance(value, Point):
            self.add_point(key, value.min, value.max)
        else:
            super().__setattr__(key, value)

    def __getitem__(self, item):
        """Return a dict of child assets with the given asset type."""
        if "." in item:
            res = {}
            child_type, offspring = item.split(".", 1)
            found = False
            for child in self.children:
                if child.asset_type == child_type:
                    found = True
                    res.update(child[offspring])
            if not found:
                raise KeyError(f"Asset type {child_type} not found.")
            return res
        else:
            res = {
                child.name: child for child in self.children if child.asset_type == item
            }
            if not res:
                logging.warning(f"Asset type {item} not found under {self}.")
            return res

    def __setitem__(self, key, value):
        if isinstance(value, Point):
            if "." in key:
                path, point_name = key.rsplit(".", 1)
                for child in self[path].values():
                    child.add_point(point_name, value.min, value.max)
            else:
                self.add_point(key, value.min, value.max)
        else:
            raise ValueError(
                "Only Point can be assigned to an asset. Use add_asset to add a child asset."
            )

    def tree(self):
        """
        Return a dict of the reference tree.
        For example:
        tree: {
            "DataCenter": {
                "DC1": {
                    "Rack": {
                        "Rack1": {
                            "DataPoints": [
                                "Power",
                                "Temperature",
                                ],
                            "Server": {
                                "Server1": {
                                    "DataPoints": [
                                        "Power",
                                        ],
                                    },
                                "Server2": {
                                    "DataPoints": [
                                        "Temperature",
                                        ],
                                    },
                                },
                            },
                        },
                    },
                },
            },
        }
        """
        _tree = self._tree()
        if not _tree:
            return {}
        tree = {self.asset_type: {self.name: _tree}}
        return tree

    def _tree(self):
        tree = {}
        for point_name in self.points.keys():
            tree.setdefault("DataPoints", []).append(point_name)
        for asset in self.children:
            inner_tree = asset._tree()
            if inner_tree:
                tree.setdefault(asset.asset_type, {})[asset.name] = inner_tree
        return tree

    def value_range(self):
        """
        Return a dict of value range for each data point.
        For example:
        value_range: {
            "DataCenter.Rack.Power": {
                "min": 0,
                "max": 100,
            },
            "DataCenter.Rack.Temperature": {
                "min": 0,
                "max": 100,
            },
            "DataCenter.Rack.Humidity": {
                "min": 0,
                "max": 100,
            },
            "DataCenter.Rack.Server.Power": {
                "min": 0,
                "max": 100,
            },
        }
        """
        range_dict = {}
        for point_name, point in self.points.items():
            entity_name = f"{self.asset_type}.{point_name}"
            range_dict[entity_name] = {"min": point.min, "max": point.max}
        for child in self.children:
            for entity_name, child_entity in child.value_range().items():
                entity_name = f"{self.asset_type}.{entity_name}"
                if entity_name in range_dict:
                    range_dict[entity_name]["min"] = min(
                        range_dict[entity_name]["min"], child_entity["min"]
                    )
                    range_dict[entity_name]["max"] = max(
                        range_dict[entity_name]["max"], child_entity["max"]
                    )
                else:
                    range_dict[entity_name] = child_entity
        return range_dict

    def uuid_map(self):
        """
        Return a dict of uuid mapping to path.
        For example:
        uuid_map: {
            "rack_power": "DataCenter.DC1.Rack.rack.Power",
            "rack_temperature": "DataCenter.DC1.Rack.rack.Temperature",
            "server_1_power": "DataCenter.DC1.Rack.rack.Server.server_1.Power",
            "server_2_power": "DataCenter.DC1.Rack.rack.Server.server_2.Power",
            "server_2_temperature": "DataCenter.DC1.Rack.rack.Server.server_2.Temperature",
        }
        """
        uuid_map = {}
        for point_name in self.points.keys():
            entity_name = f"{self.asset_type}.{self.name}.{point_name}"
            uuid_map[self._uuid(point_name)] = entity_name
        for child in self.children:
            for uuid, entity_name in child.uuid_map().items():
                uuid_map[uuid] = f"{self.asset_type}.{self.name}.{entity_name}"
        return uuid_map

    def _uuid(self, point_name):
        return f"{self.name}_{point_name}".lower().replace(" ", "_")

    def search(self, asset_name):
        if asset_name == self.name:
            return self
        for child in self.children:
            if child.name == asset_name:
                return child
            else:
                res = child.search(asset_name)
                if res:
                    return res

    def parse_dt_construction(self, data, type_maps, skip_keys):
        construction = data.get("constructions", {})
        for asset_type, assets in construction.items():
            if asset_type in skip_keys:
                continue
            asset_type = type_maps.get(
                asset_type, asset_type[0].upper() + asset_type[1:]
            )
            for asset_name, asset_info in assets.items():
                child = self.add_asset(asset_type, asset_name)
                child.parse_dt_construction(asset_info, type_maps, skip_keys)

    def parse_dt_inputs(self, data, point_maps=None):
        inputs = data.get("inputs", {})
        for asset_type, assets in inputs.items():
            for asset_name, data_points in assets.items():
                asset = self.search(asset_name)
                for data_point, value in data_points.items():
                    data_point = point_maps.get(
                        data_point, data_point[0].upper() + data_point[1:]
                    )
                    asset.add_point(data_point, value, value)

    def load_room_from_dt(self, dt, type_maps=None, point_maps=None, skip_keys=None):
        """
        Generate reference tree from a dt file
        """
        type_maps = {
            "acus": "ACU",
            "racks": "Rack",
            "servers": "Server",
            "sensors": "Sensor",
        } | (type_maps or {})
        point_maps = point_maps or {}
        skip_keys = set(skip_keys or []) | {"raisedFloor"}
        if isinstance(dt, str):
            with open(dt) as f:
                dt = json.load(f)
        room = Asset("DataHall", dt["meta"]["name"])
        room.parse_dt_construction(dt, type_maps, skip_keys)
        room.parse_dt_inputs(dt, point_maps)
        self.add_child(room)

    def to_snapshot_frame(self, parent_asset=None):
        """
        Return a pandas.DataFrame containing columns asset,asset_type,parent_asset,data_point,value,unit,uuid, where unit is always None and value is always randomised between min and max.
        """
        data = []
        for data_point, point in self.points.items():
            data.append(
                pd.Series(
                    {
                        "asset": self.name,
                        "asset_type": self.asset_type,
                        "parent_asset": parent_asset.name if parent_asset else None,
                        "data_point": data_point,
                        "value": np.random.uniform(point.min, point.max),
                        "unit": None,
                        "uuid": self._uuid(data_point),
                    }
                )
            )
        if not data:
            data.append(
                pd.Series(
                    {
                        "asset": self.name,
                        "asset_type": self.asset_type,
                        "parent_asset": parent_asset.name if parent_asset else None,
                        "data_point": None,
                        "value": None,
                        "unit": None,
                        "uuid": None,
                    }
                )
            )
        df = pd.DataFrame(data)
        for asset in self.children:
            df = pd.concat([df, asset.to_snapshot_frame(parent_asset=self)])
        return df

    @staticmethod
    def _to_yaml(data, file_name=None):
        data = yaml.dump(data)
        if file_name:
            with open(file_name, "w") as f:
                f.write(data)
        return data

    def to_reference(self, as_yaml=False, file_name=None):
        res = {
            "tree": self.tree(),
            "value_range": self.value_range(),
            "uuid_map": self.uuid_map(),
        }
        if as_yaml:
            return self._to_yaml(res, file_name=file_name)
        return res

    # $asset_library_name: fxms_assets
    # $asset_library_path: scenario
    def to_schema(self, as_yaml=False, library_name="tiro", library_path="scenario", file_name=None):
        draft_gen = DraftGenerator(dataframe=self.to_snapshot_frame())
        res = draft_gen.schema
        res["$asset_library_name"] = library_name
        res["$asset_library_path"] = library_path
        if as_yaml:
            return self._to_yaml(res, file_name=file_name)
        return res

    def to_uses(self, as_yaml=False, file_name=None):
        draft_gen = DraftGenerator(dataframe=self.to_snapshot_frame())
        res = draft_gen.uses
        if as_yaml:
            return self._to_yaml(res, file_name=file_name)
        return res

    def _to_library_class(self):
        """Generate python code for a library class."""
        lines = [
            f"class {self.asset_type}(Entity):"
        ]
        if self.points:
            for point_name, point in self.points.items():
                lines.append(f"    {point_name}: RangedFloatTelemetry({point.min}, {point.max})")
        else:
            lines.append(f"    pass")
        return "\n".join(lines)

    def _to_library(self, existing_classes=None):
        existing_classes = existing_classes or {}
        existing_classes[self.asset_type] = self._to_library_class()
        for child in self.children:
            if child.asset_type not in existing_classes:
                child._to_library(existing_classes)
        return existing_classes

    def to_library(self, file_name=None):
        import_str = "from tiro.core.entity import Entity\n" \
                     "from tiro.core.telemetry import RangedFloatTelemetry"
        res = (os.linesep * 3).join([import_str, *self._to_library().values()])
        if file_name:
            with open(file_name, "w") as f:
                f.write(res)
        return res


class GPTPointGenerator:
    """
    A class that utilise GPT-3/4 to help data point generation.
    The GPT can help to estimate reasonable value ranges of a data point.
    For example, if given a point path like "DataCenter.Rack.Server.Power" and the unit "W", the GPT can help to estimate a reasonable value range for the power consumption of a server.
    """

    SYSTEM_PROMPT = """I will give a list of data point paths for a {asset} in {country}, please estimate a reasonable value range for each input. 
    Example:
        Q:
          Chiller.Power in W
          CoolingTower.CoolingWaterFlowRate in m^3/s

        A:
            Chiller.Power: 0, 100
            CoolingTower.CoolingWaterFlowRate: 0.2, 0.5

    Return only the output without any explanations. Each line contains one data point.
    """

    def __init__(self, root, token, model="gpt-4", country="Singapore", asset="DataCenter"):
        self.root = root
        self.token = token
        self.model = model
        self.country = country
        self.asset = asset
        self.path_list = []

    def add_path(self, path, unit=None):
        self.path_list.append((path, unit))

    def generate(self):
        """
        Each path in path_list is a tuple of (path, unit). The return should be a dict of {path: (min, max)}.
        """
        import openai

        openai.api_key = self.token
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": self.SYSTEM_PROMPT.format(country=self.country, asset=self.asset),
                },
                {
                    "role": "user",
                    "content": "\n".join(
                        [f"{path} in {unit}" if unit else path for path, unit in self.path_list]
                    ),
                },
            ],
        )
        res = {}
        try:
            answer = response.choices[0]["message"]["content"]
            for line in answer.split("\n"):
                if line.strip():
                    path, value_range = line.split(":")
                    min_value, max_value = value_range.split(",")
                    res[path.strip()] = Point(
                        float(min_value.strip()), float(max_value.strip())
                    )
        except Exception as e:
            logging.error("Unable to parse GPT response:")
            logging.error(response.choices[0])
            raise e
        return res

    def complete_asset(self):
        """
        Complete data points for an asset.
        """
        for path, point in self.generate().items():
            self.root[path] = point
