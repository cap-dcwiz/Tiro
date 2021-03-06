import logging
from datetime import timedelta, datetime
from pathlib import Path
from typing import Optional, Literal
from rich import print

import pandas as pd

from utinni.table.preprocess import PreProcessorForTSTable

try:
    from utinni.table.table import TimeSeriesPrimaryTable, PrimaryTable
    from utinni.types import ValueType
    from utinni.pump import InfluxDBDataPump
except ImportError:
    raise ImportError("Utinni is not available. Please install Utinni first.")

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
        value = super(PreProcessorForTiroTSTable, self).preprocess_dim_2(value, config, table_meta)
        key = table_meta["group_by"]
        if key == "asset_path":
            return value
        return getattr(
            value.groupby(lambda x: self._get_tag_from_asset_path(x, key), axis=1),
            table_meta["asset_agg_fn"]
        )(**table_meta.get("asset_agg_fn_kwargs", {}))


class TimeSeriesPrimaryTableForTiro(TimeSeriesPrimaryTable):
    PreProcessorClass = PreProcessorForTiroTSTable


class TiroTSPump(InfluxDBDataPump):
    def __init__(self, *args,
                 scenario: Scenario | str | Path,
                 uses: Optional[list[str | Path]] = None,
                 arangodb_db="tiro",
                 arangodb_graph="scenario",
                 arangodb_hosts="http://localhost:8529",
                 arangodb_auth=None,
                 arangodb_agent=None,
                 **kwargs):
        super(TiroTSPump, self).__init__(*args,
                                         **kwargs)
        uses = uses or []
        if isinstance(scenario, Scenario):
            self.scenario = scenario
            for use in uses:
                self.scenario.requires(use)
        else:
            self.scenario = Scenario.from_yaml(scenario, *uses)
        if arangodb_agent is None:
            self._arangodb_agent_params = dict(scenario=scenario,
                                               db_name=arangodb_db,
                                               graph_name=arangodb_graph,
                                               auth_info=arangodb_auth,
                                               hosts=arangodb_hosts)
        else:
            self._arangodb_agent_params = None
            if arangodb_agent.scenario is None:
                arangodb_agent.set_scenario(scenario)
        self._arangodb_agent = arangodb_agent

    @property
    def arangodb_agent(self):
        if self._arangodb_agent is None:
            if self._arangodb_agent is not None:
                agent = ArangoAgent(**self._arangodb_agent_params)
            else:
                agent = self.context.clients.get("arangodb")
            if agent and agent.scenario is None:
                agent.set_scenario(self.scenario)
            self._arangodb_agent = agent
        return self._arangodb_agent

    def gen_table(self,
                  query: Optional[str | dict | Path] = ".*",
                  type: Literal["historian", "status"] = "historian",
                  column: str = "asset_path",
                  asset_agg_fn: str = "mean",
                  asset_agg_fn_kwargs: dict = None,
                  time_agg_fn: str = "last",
                  fill_with_graph: bool = True,
                  as_dataframe: bool = False,
                  include_tags: list[str] | str = "all",
                  value_only: bool = False,
                  # When query status, the telemetries updated before (now - max_time_diff) will be ignored.
                  max_time_diff: Optional[float] = 600,
                  ) -> PrimaryTable:
        if type == "historian":
            return self.gen_historian_table(pattern_or_uses=query,
                                            column=column,
                                            asset_agg_fn=asset_agg_fn,
                                            asset_agg_fn_kwargs=asset_agg_fn_kwargs or {},
                                            time_agg_fn=time_agg_fn,  # Careful!
                                            only_ts=not fill_with_graph,
                                            time_diff=max_time_diff,
                                            )
        elif type == "status":
            return self.gen_status_table(query_or_regex=query,
                                         as_dataframe=as_dataframe,
                                         value_only=value_only,
                                         include_tags=include_tags,
                                         time_diff=max_time_diff)

    def gen_historian_table(self,
                            pattern_or_uses: str | dict | Path,
                            column: str,
                            asset_agg_fn: str,
                            asset_agg_fn_kwargs: dict,
                            time_agg_fn: str,
                            only_ts: bool,
                            time_diff: float,
                            ) -> TimeSeriesPrimaryTable:
        paths = list(self.scenario.match_data_points(pattern_or_uses))
        if not paths:
            raise RuntimeError(f"Cannot find data points matching the pattern \"{pattern_or_uses}\"")
        table = super(TiroTSPump, self).gen_table(column="asset_path", agg_fn=time_agg_fn, path=paths,
                                                  table_cls=TimeSeriesPrimaryTableForTiro)
        logging.debug(f"paths: {';'.join(paths)}")
        table.set_meta("asset_agg_fn", asset_agg_fn)
        table.set_meta("asset_agg_fn_kwargs", asset_agg_fn_kwargs)
        table.set_meta("table_type", "historian")
        table.set_meta("only_ts", only_ts)
        table.set_meta("pattern_or_uses", pattern_or_uses)
        table.set_meta("time_diff", time_diff)
        table.set_meta("group_by", column)
        return table

    def gen_status_table(self,
                         query_or_regex: str | dict | Path,
                         as_dataframe: bool,
                         value_only: bool,
                         include_tags: list[str],
                         time_diff: float
                         ) -> PrimaryTable:
        return PrimaryTable(context=self.context,
                            pump=self,
                            fields=None,
                            meta=dict(table_type="status",
                                      query_or_regex=query_or_regex,
                                      as_df=as_dataframe,
                                      value_only=value_only,
                                      include_tags=include_tags,
                                      time_diff=time_diff))

    def get_data(self, table: PrimaryTable, fields) -> ValueType:
        table_type = table.meta["table_type"]
        if table_type == "historian" and isinstance(table, TimeSeriesPrimaryTable):
            return self.get_ts_data(table, fields)
        elif table_type == "status":
            return self.get_status_data(table)
        else:
            raise RuntimeError(f"Wrong Tiro table type: {table_type}")

    def get_ts_data(self, table: TimeSeriesPrimaryTable, fields) -> ValueType:
        try:
            data = super(TiroTSPump, self).get_data(table, fields=fields)
            if not table.meta["only_ts"]:
                if fields:
                    missing_fields = set(f for f in fields if f not in data)
                    if missing_fields:
                        data |= self.fill_data_from_graph_db(table, missing_fields)
                else:
                    data |= {
                        k: v for k, v in self.fill_data_from_graph_db(table, None).items()
                        if k not in data
                    }
        except RuntimeError:
            if not table.meta["only_ts"]:
                data = self.fill_data_from_graph_db(table, fields)
            else:
                data = {}
        return data

    def get_status_data(self, table: PrimaryTable) -> ValueType:
        query_or_regex = table.meta["query_or_regex"]
        as_dataframe = table.meta["as_df"]
        query_params = dict(
            as_dataframe=as_dataframe,
            value_only=table.meta["value_only"],
            include_tags=table.meta["include_tags"],
            max_time_diff=table.meta["time_diff"]
        )
        if isinstance(query_or_regex, str):
            res = self.arangodb_agent.query_by_regex(query_or_regex, **query_params)
        else:
            res = self.arangodb_agent.query_by_qpath(query_or_regex, **query_params)
        if as_dataframe:
            if not res.empty:
                return {field: g.drop(columns=["field"]) for field, g in res.groupby("field")}
            else:
                return {}
        else:
            return res

    def fill_data_from_graph_db(self, table: TimeSeriesPrimaryTable, fields) -> ValueType:
        column = table.meta["group_by"]
        asset_agg_fn = table.meta["asset_agg_fn"]
        pattern_or_uses = table.meta["pattern_or_uses"]
        time_diff = table.meta["time_diff"]
        config = table.config
        missing_data = []
        for path, value in self.arangodb_agent.query_attributes_and_missing(
                pattern_or_uses=pattern_or_uses,
                max_time_diff=time_diff
        ).items():
            data_point = self.scenario.data_point_path_to_tags(path) | value
            if fields and path.split(PATH_SEP)[-1] not in fields:
                continue
            missing_data.append(data_point)
        index = gen_index(config.start, config.stop, config.step)
        results = {}
        field: str
        if missing_data:
            for field, df in pd.DataFrame(missing_data).groupby("field"):
                series = getattr(df.groupby(column).value, asset_agg_fn)()
                results[field] = pd.DataFrame(data=[series for _ in index], index=index)
        return results
