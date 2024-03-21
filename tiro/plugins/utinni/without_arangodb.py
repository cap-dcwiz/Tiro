from loguru import logger as logging
from datetime import timedelta, datetime
from pathlib import Path
from typing import Optional, Literal

import pandas as pd

from utinni.exception import NoValidDataFoundException
from utinni.table.preprocess import PreProcessorForTSTable
from utinni.table.table import TimeSeriesPrimaryTable, PrimaryTable
from utinni.types import ValueType
from utinni.pump import InfluxDBDataPump

from tiro.core import Scenario
from tiro.core.utils import PATH_SEP, split_path
from tiro.plugins.graph.agent import ArangoAgent


def _timeshift_by_epoch(dt: datetime, step: timedelta):
    step_seconds = step.total_seconds()
    ts = dt.timestamp()
    return timedelta(seconds=ts - ts // step_seconds * step_seconds)


def gen_index(start, stop, step):
    if isinstance(step, timedelta):
        start -= _timeshift_by_epoch(start, step)
        stop -= _timeshift_by_epoch(stop, step)
    return pd.date_range(start, stop, freq=step)


class PreProcessorForTiroTSTable(PreProcessorForTSTable):
    @staticmethod
    def _get_tag_from_asset_path(path, name):
        path = split_path(path)
        if name == "path":
            return PATH_SEP.join(path[i] for i in range(0, len(path), 2))
        if name in path:
            return path[path.index(name) + 1]
        else:
            return None

    def preprocess_dim_2(self, value, config, table_meta):
        key = table_meta["group_by"]
        group_by = lambda x: self._get_tag_from_asset_path(x, key)
        agg_fn = table_meta["asset_agg_fn"]
        agg_fn_kwargs = table_meta.get("asset_agg_fn_kwargs", {})
        if table_meta.get("table_type") == "status":
            value = value.set_index("asset_path", drop=True)["_value"]
            if key == "asset_path":
                return value
            else:
                return getattr(value.groupby(group_by), agg_fn)(**agg_fn_kwargs)
        else:
            value = super(PreProcessorForTiroTSTable, self).preprocess_dim_2(
                value, config, table_meta
            )
            if key == "asset_path":
                return value
            else:
                return getattr(value.T.groupby(group_by), agg_fn)(**agg_fn_kwargs).T


class TimeSeriesPrimaryTableForTiro(TimeSeriesPrimaryTable):
    PreProcessorClass = PreProcessorForTiroTSTable
    # PreProcessorClass = NullPreProcessor


class TiroTSPump(InfluxDBDataPump):
    def __init__(
            self,
            *args,
            scenario: Scenario | str | Path,
            uses: Optional[list[str | Path]] = None,
            arangodb_db="tiro",
            arangodb_graph="scenario",
            arangodb_hosts=None,
            arangodb_auth=None,
            arangodb_agent=None,
            **kwargs,
    ):
        super(TiroTSPump, self).__init__(*args, **kwargs)
        uses = uses or []
        if isinstance(scenario, Scenario):
            self.scenario = scenario
            for use in uses:
                self.scenario.requires(use)
        else:
            self.scenario = Scenario.from_yaml(scenario, *uses)

    def gen_table(
            self,
            query: Optional[str | dict | Path] = ".*",
            type: Literal["historian", "status"] = "historian",
            column: str = "asset_path",
            asset_agg_fn: str = "mean",
            asset_agg_fn_kwargs: dict = None,
            time_agg_fn: str = "last",
            # When query status, the telemetries updated before (now - max_time_diff) will be ignored.
            max_time_diff: Optional[float] = 600,
    ) -> PrimaryTable:
        paths = list(self.scenario.match_data_points(query))
        if not paths:
            raise RuntimeError(
                f'Cannot find data points matching the pattern "{query}"'
            )
        table = super(TiroTSPump, self).gen_table(
            column="asset_path",
            agg_fn=time_agg_fn,
            path=paths,
            table_cls=TimeSeriesPrimaryTableForTiro,
        )
        table.set_meta("asset_agg_fn", asset_agg_fn)
        table.set_meta("asset_agg_fn_kwargs", asset_agg_fn_kwargs or {})
        table.set_meta("table_type", type)
        table.set_meta("pattern_or_uses", query)
        table.set_meta("group_by", column)
        if type == "status":
            table.set_meta("time_delta", timedelta(seconds=max_time_diff))
        return table

    def gen_historian_table(
            self,
            pattern_or_uses: str | dict | Path,
            column: str,
            asset_agg_fn: str,
            asset_agg_fn_kwargs: dict,
            time_agg_fn: str,
    ) -> TimeSeriesPrimaryTable:
        paths = list(self.scenario.match_data_points(pattern_or_uses))
        if not paths:
            raise RuntimeError(
                f'Cannot find data points matching the pattern "{pattern_or_uses}"'
            )
        table = super(TiroTSPump, self).gen_table(
            column="asset_path",
            agg_fn=time_agg_fn,
            path=paths,
            table_cls=TimeSeriesPrimaryTableForTiro,
        )
        table.set_meta("asset_agg_fn", asset_agg_fn)
        table.set_meta("asset_agg_fn_kwargs", asset_agg_fn_kwargs)
        table.set_meta("table_type", "historian")
        table.set_meta("pattern_or_uses", pattern_or_uses)
        table.set_meta("group_by", column)
        return table

    def get_data(self, table: PrimaryTable, fields) -> ValueType:
        try:
            data = super(TiroTSPump, self).get_data(table, fields=fields)
        except NoValidDataFoundException:
            logging.warning(
                f"{table.name or table}: "
                f"Failed to get data from Tiro, WILL NOT try to get data from ArangoDB"
            )
            raise
        return data
