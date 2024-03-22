import os

import json
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np
import yaml
from loguru import logger as logging

from tiro.core.draft import DraftGenerator

from .use2query import use2query


class Point:
    def __init__(
        self,
        _min: float | int,
        _max: float | int,
        unit: Optional[str] = None,
        uuid: Optional[str] = None,
    ):
        self.min = _min
        self.max = _max
        self.unit = unit
        self.uuid = uuid

    def __str__(self):
        return f"Point({self.min}, {self.max}, {self.unit})"

    def __repr__(self):
        return f"Point({self.min}, {self.max}, {self.unit})"


class Asset:
    def __init__(self, asset_type: str, name: str):
        self.asset_type: str = asset_type
        self.name: str = name
        self.children: list[Asset] = []
        self.points: dict[str, Point] = {}

    def add_child(self, asset: "Asset") -> "Asset":
        self.children.append(asset)
        return asset

    def add_asset(self, asset_type: str, name: str) -> "Asset":
        return self.add_child(Asset(asset_type, name))

    def add_point(
        self,
        point_name: str,
        _min: float | int,
        _max: float | int,
        unit: Optional[str] = None,
        uuid: Optional[str] = None,
    ) -> Point:
        old_point = self.points.get(point_name, None)
        if old_point is not None:
            unit = unit or old_point.unit
            uuid = uuid or old_point.uuid
        point = Point(_min, _max, unit, uuid)
        self.points[point_name] = point
        return point

    def add_point_to_children(
        self,
        path: str,
        point_name: str,
        _min: float | int,
        _max: float | int,
        unit: Optional[str] = None,
        uuid: Optional[str] = None,
    ) -> None:
        """
        Add a point to all children with the given path.
        For example, if the path is ["Rack", "Server"], then the point will be added to all servers.
        """
        for child in self[path].values():
            child.add_point(point_name, _min, _max, unit, uuid)

    def __str__(self):
        return f"{self.asset_type}#{self.name}"

    def __setattr__(self, key, value):
        if isinstance(value, Point):
            self.add_point(key, value.min, value.max, value.unit, value.uuid)
        else:
            super().__setattr__(key, value)

    def __getitem__(self, item):
        return self.get_children(item, ignore_not_found=False)

    def get_children(
        self, item: str, ignore_not_found: bool = False
    ) -> dict[str, "Asset"]:
        """Return a dict of child assets with the given asset type."""
        if "." in item:
            res = {}
            child_type, offspring = item.split(".", 1)
            found = False
            for child in self.children:
                if child.asset_type == child_type:
                    found = True
                    res.update(
                        child.get_children(offspring, ignore_not_found=ignore_not_found)
                    )
            if not found and not ignore_not_found:
                raise KeyError(f"Asset type {child_type} not found.")
            return res
        else:
            res = {
                child.name: child for child in self.children if child.asset_type == item
            }
            if not res:
                logging.warning(f"Asset type {item} not found under {self}.")
            return res

    def __setitem__(self, key: str, value: Point) -> None:
        if isinstance(value, Point):
            if "." in key:
                path, point_name = key.rsplit(".", 1)
                for child in self.get_children(path, ignore_not_found=True).values():
                    child.add_point(
                        point_name, value.min, value.max, value.unit, value.uuid
                    )
            else:
                self.add_point(key, value.min, value.max, value.unit, value.uuid)
        else:
            raise ValueError(
                "Only Point can be assigned to an asset. Use add_asset to add a child asset."
            )

    def tree(self) -> dict:
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

    def _tree(self) -> dict:
        tree = {}
        for point_name in self.points.keys():
            tree.setdefault("DataPoints", []).append(point_name)
        for asset in self.children:
            inner_tree = asset._tree()
            if inner_tree:
                tree.setdefault(asset.asset_type, {})[asset.name] = inner_tree
        return tree

    def value_range(self) -> dict:
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

    def uuid_map(self) -> dict[str, str]:
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
        for point_name, point in self.points.items():
            entity_name = f"{self.asset_type}.{self.name}.{point_name}"
            uuid_map[point.uuid or self._uuid(point_name)] = entity_name
        for child in self.children:
            for uuid, entity_name in child.uuid_map().items():
                uuid_map[uuid] = f"{self.asset_type}.{self.name}.{entity_name}"
        return uuid_map

    def _uuid(self, point_name: str) -> str:
        return f"{self.name}_{point_name}".lower().replace(" ", "_")

    def search(self, asset_name: str) -> Optional["Asset"]:
        if asset_name == self.name:
            return self
        for child in self.children:
            if child.name == asset_name:
                return child
            else:
                res = child.search(asset_name)
                if res:
                    return res

    def parse_dt_construction(
        self, data: dict, type_maps: dict, skip_keys: set[str]
    ) -> None:
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

    def parse_dt_inputs(self, data: dict, point_maps: dict) -> None:
        inputs = data.get("inputs", {})
        for asset_type, assets in inputs.items():
            for asset_name, data_points in assets.items():
                asset = self.search(asset_name)
                for data_point, value in data_points.items():
                    data_point = point_maps.get(
                        data_point, data_point[0].upper() + data_point[1:]
                    )
                    asset.add_point(data_point, value, value)

    def load_room_from_dt(
        self,
        dt: dict,
        type_maps: dict = None,
        point_maps: dict = None,
        skip_keys: set[str] = None,
    ) -> "Asset":
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
        return self

    def to_snapshot_frame(self, parent_asset: Optional["Asset"] = None) -> pd.DataFrame:
        """
        Return a pandas.DataFrame containing columns asset,asset_type,parent_asset,data_point,value,unit,uuid,
        where unit is always None and value is always randomised between min and max.
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
                        "value": np.random.uniform(point.min, point.max)
                        if point.min < point.max
                        else point.min,
                        "unit": None,
                        "uuid": self._uuid(data_point),
                    }
                )
            )
        if not data and self.children:
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
            child_df = asset.to_snapshot_frame(parent_asset=self)
            if child_df.empty:
                continue
            elif df.empty:
                df = child_df
            else:
                df = pd.concat([df.astype(child_df.dtypes), child_df.astype(df.dtypes)])
        return df

    def _load_from_snapshot(self, df: pd.DataFrame) -> None:
        """
        Load data from a snapshot dataframe.
        """
        for item in df[(df.asset == self.name) & (~df.data_point.isna())].itertuples():
            value = getattr(item, "value", 0.0)
            self.add_point(
                item.data_point,
                value,
                value,
                getattr(item, "unit", None),
                getattr(
                    item, "uuid", f"{self.asset_type}_{self.name}_{item.data_point}"
                ),
            )
        for item in df[df.parent_asset == self.name].itertuples():
            child = self.add_asset(item.asset_type, item.asset)
            child._load_from_snapshot(df)

    @classmethod
    def from_snapshot(
        cls, df: pd.DataFrame, root_type: str = "Root", root_name: str = "Root"
    ) -> "Asset":
        """
        Load data from a snapshot dataframe.
        """
        assets = []
        if "masked" in df.columns:
            df = df[df.masked != 1]
        top_level = df[df["parent_asset"].isna()]
        for asset, sub_df in top_level.groupby("asset"):
            asset_type = sub_df["asset_type"].iloc[0]
            asset = cls(asset_type, asset)
            asset._load_from_snapshot(df)
            assets.append(asset)
        if len(assets) == 1:
            return assets[0]
        else:
            root = cls(root_type, root_name)
            for asset in assets:
                root.add_child(asset)
            return root

    def all_point_path(self) -> dict[str, Point]:
        """
        Return a list of all point paths.
        """
        res = {}
        for point_name, point in self.points.items():
            res[f"{self.asset_type}.{point_name}"] = point
        for child in self.children:
            res.update(
                {
                    f"{self.asset_type}.{child_name}": child
                    for child_name, child in child.all_point_path().items()
                }
            )
        return res

    @staticmethod
    def _to_yaml(data: dict, file_name: Optional[Path | str] = None) -> Optional[str]:
        data = yaml.dump(data)
        if file_name:
            if isinstance(file_name, str):
                file_name = Path(file_name)
            with file_name.open("w") as f:
                f.write(data)
        else:
            return data

    def to_reference(
        self, as_yaml: bool = False, file_name: Optional[Path | str] = None
    ) -> dict | str:
        res = {
            "tree": self.tree(),
            "value_range": self.value_range(),
            "uuid_map": self.uuid_map(),
        }
        if as_yaml:
            return self._to_yaml(res, file_name=file_name)
        else:
            return res

    # $asset_library_name: assets
    # $asset_library_path: scenario
    def to_schema(
        self,
        as_yaml: bool = False,
        library_name: bool = "assets",
        library_path: str = "scenario",
        file_name: Optional[Path | str] = None,
    ) -> dict | str:
        draft_gen = DraftGenerator(dataframe=self.to_snapshot_frame())
        res = draft_gen.schema
        res["$asset_library_name"] = library_name
        res["$asset_library_path"] = library_path
        if as_yaml:
            return self._to_yaml(res, file_name=file_name)
        else:
            return res

    def to_uses(
        self, as_yaml: bool = False, file_name: Optional[Path | str] = None
    ) -> dict | str:
        draft_gen = DraftGenerator(dataframe=self.to_snapshot_frame())
        res = draft_gen.uses
        if as_yaml:
            return self._to_yaml(res, file_name=file_name)
        else:
            return res

    def _to_library_class(self) -> str:
        """Generate python code for a library class."""
        lines = [f"class {self.asset_type}(Entity):"]
        if self.points:
            for point_name, point in self.points.items():
                lines.append(
                    f"    {point_name}: RangedFloatTelemetry({point.min}, {point.max})"
                )
        else:
            lines.append(f"    pass")
        return "\n".join(lines)

    def _to_library(self, existing_classes: dict = None) -> dict:
        existing_classes = existing_classes or {}
        if self.asset_type not in existing_classes:
            existing_classes[self.asset_type] = self._to_library_class()
        for child in self.children:
            child._to_library(existing_classes)
        return existing_classes

    def to_library(self, file_name: Optional[Path | str] = None) -> str | None:
        import_str = (
            "from tiro.core import Entity\n"
            "from tiro.utils import RangedFloatTelemetry"
        )
        res = (os.linesep * 3).join([import_str, *self._to_library().values()])
        if file_name:
            if isinstance(file_name, str):
                file_name = Path(file_name)
            with file_name.open("w") as f:
                f.write(res)
        else:
            return res

    def gen_scenario(
        self,
        path: Path | str,
        gen_query: bool = False,
        query_path: Optional[Path | str] = None,
    ) -> None:
        if isinstance(path, str):
            path = Path(path)
        self.to_schema(as_yaml=True, file_name=path / "scenario.yaml")
        self.to_uses(as_yaml=True, file_name=path / "uses.yaml")
        self.to_reference(as_yaml=True, file_name=path / "reference.yaml")
        self.to_library(file_name=path / "assets" / "__init__.py")
        if gen_query:
            if isinstance(query_path, str):
                query_path = Path(query_path)
            query_path = query_path or (path / "query.yaml")
            use2query(path / "uses.yaml", query_path)
