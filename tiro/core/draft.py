import re
from pathlib import Path
from typing import Optional

import pandas as pd
from pandas import DataFrame

from .utils import split_path, insert_data_point_to_dict


class DraftGenerator:
    def __init__(self, dataframe: Optional[DataFrame] = None, csv_file: Optional[Path] = None):
        self.df: DataFrame = dataframe or pd.read_csv(csv_file)
        self.df["data_point"] = self.df.data_point.apply(self.format_name)
        self.df["asset_type"] = self.df.asset_type.apply(self.format_name)

        self.parent_dict: dict[str, str] = \
            self.df.groupby("asset").parent_asset.first().to_dict()
        self.type_dict: dict[str, str] = \
            self.df.groupby("asset").asset_type.first().to_dict()
        self.data_point_dict: dict[str, dict[tuple[str, str], int]] = \
            self.df.groupby("asset").data_point.unique().to_dict()

        self.df["parent_type"] = self.df.parent_asset.apply(lambda x: self.type_dict.get(x, None))
        self.df["path"] = self.df.asset.apply(self.get_asset_path)
        self.df["type_path"] = self.df.apply(lambda s: f"{self.get_type_path(s.asset)}.{s.data_point}", axis=1)

        self.count_info = self.get_children_counts()

    @staticmethod
    def format_name(name):
        if isinstance(name, str):
            name = "".join([re.sub(r"\W|^(?=\d)", "", item) for item in name.strip().split()])
        return name

    def get_children_counts(self) -> dict[str, dict[tuple[str, str], int]]:
        cc = self.df \
            .groupby(["parent_type", "asset_type", "parent_asset"]) \
            .asset.nunique() \
            .unstack("parent_asset") \
            .fillna(0).astype(int)
        return dict(min=cc.min(axis=1).to_dict(), max=cc.max(axis=1).to_dict())

    def get_asset_path(self, asset: str) -> str:
        component = f"{self.type_dict[asset]}.{asset}"
        parent = self.parent_dict.get(asset, None)
        if parent:
            return f"{self.get_asset_path(parent)}.{component}"
        else:
            return component

    def get_type_path(self, asset: str) -> str:
        component = f"{self.type_dict[asset]}"
        parent = self.parent_dict.get(asset, None)
        if parent:
            return f"{self.get_type_path(parent)}.{component}"
        else:
            return component

    def insert_into_schema(self,
                           path: str | list[str],
                           schema: dict,
                           parent_type: Optional[str] = None):
        path = split_path(path)
        if path:
            asset_type = path.pop(0)
            path.pop(0)
            if asset_type not in schema:
                schema[asset_type] = {"$type": asset_type, "$number": 0}
            count_key = parent_type, asset_type
            if count_key in self.count_info["min"]:
                min_num = self.count_info["min"][count_key]
                max_num = self.count_info["max"][count_key]
                if min_num == max_num:
                    schema[asset_type]["$number"] = min_num
                else:
                    schema[asset_type]["$number"] = f"{min_num}-{max_num}"
            else:
                schema[asset_type]["$number"] += 1
            self.insert_into_schema(path, schema[asset_type], asset_type)

    def insert_into_uses(self,
                         path: str | list[str],
                         data_point: str,
                         uses: dict):
        path = split_path(path)
        if path:
            asset_type = path.pop(0)
            path.pop(0)
            if asset_type not in uses:
                uses[asset_type] = {}
            self.insert_into_uses(path, data_point, uses[asset_type])
        else:
            uses[data_point] = None

    def post_process_uses(self, uses: dict) -> list:
        res = []
        for k in sorted(uses.keys()):
            v = uses[k]
            if v:
                v = self.post_process_uses(v)
                res.append({k: v})
            else:
                res.append(k)
        return res

    @property
    def schema(self):
        schema = {}
        for path in self.df.path.unique():
            self.insert_into_schema(path, schema)
        return schema

    @property
    def uses(self):
        uses = {}
        for row in self.df[~self.df.data_point.isna()].itertuples():
            self.insert_into_uses(row.path, row.data_point, uses)
        return self.post_process_uses(uses)

    @property
    def sample(self):
        tree = {}
        for path, dps in self.df[~self.df.data_point.isna()].groupby("path").data_point.unique().items():
            insert_data_point_to_dict(path, list(dps), tree)
        value_range = self.df.groupby("type_path").value.agg([min, max]).dropna().to_dict(orient="index")
        return dict(tree=tree, value_range=value_range)
