from datetime import timedelta, datetime
from pathlib import Path
from typing import Optional, Literal

import pandas as pd
from arango import ArangoClient
from utinni.table.table import TimeSeriesPrimaryTable
from utinni.types import ValueType

from tiro.core import Scenario
from utinni.pump import InfluxDBDataPump

from tiro.core.utils import PATH_SEP, split_path
from tiro.plugins.arango import ArangoAgent


def _timeshift_by_epoch(dt: datetime, step: timedelta):
    step_seconds = step.total_seconds()
    ts = dt.timestamp()
    return timedelta(seconds=ts - ts // step_seconds * step_seconds)


def gen_index(start, stop, step):
    if isinstance(step, timedelta):
        start -= _timeshift_by_epoch(start, step)
        stop -= _timeshift_by_epoch(stop, step)
    return pd.date_range(start, stop, freq=step)


class TiroTSPump(InfluxDBDataPump):
    def __init__(self, *args,
                 scenario: Scenario | str | Path,
                 uses: Optional[list[str | Path]] = None,
                 influxdb_url="http://localhost:8086",
                 influxdb_token="influxdb_token",
                 influxdb_org="tiro",
                 influxdb_bucket="tiro",
                 influxdb_measurement="tiro",
                 arangodb_db="tiro",
                 arangodb_graph="scenario",
                 arangodb_hosts="http://localhost:8529",
                 arangodb_auth=None,
                 **kwargs):
        super(TiroTSPump, self).__init__(*args,
                                         url=influxdb_url,
                                         token=influxdb_token,
                                         org=influxdb_org,
                                         bucket=influxdb_bucket,
                                         measurement=influxdb_measurement,
                                         **kwargs)
        uses = uses or []
        if isinstance(scenario, Scenario):
            self.scenario = scenario
            for use in uses:
                self.scenario.requires(use)
        else:
            self.scenario = Scenario.from_yaml(scenario, *uses)
        self.graph_db_agent = ArangoAgent(scenario,
                                          db_name=arangodb_db,
                                          graph_name=arangodb_graph,
                                          client=ArangoClient(hosts=arangodb_hosts),
                                          auth_info=arangodb_auth)

    # @property
    # def graph_db_agent(self):
    #     if not self._graph_db_agent:
    #         print(self.config.arangodb)
    #         self._graph_db_agent = ArangoAgent(
    #             scenario=self.scenario,
    #             db_name=self.config.arangodb.db,
    #             graph_name=self.config.arangodb.graph,
    #             client=ArangoClient(hosts=self.config.arangodb.hosts),
    #             auth_info=self.config.arangodb.auth
    #         )
    #     return self._graph_db_agent

    def gen_table(self,
                  pattern: str,
                  column: str = "asset_path",
                  agg_fn: Literal["mean", "max", "min"] = "mean",
                  only_ts: bool = True,
                  fill_with_default: bool = False
                  ):
        paths = list(self.scenario.match_data_points(pattern))
        table = super(TiroTSPump, self).gen_table(column=column, agg_fn=agg_fn, path=paths)
        table.set_meta("only_ts", only_ts)
        table.set_meta("fill_with_default", fill_with_default)
        table.set_meta("pattern", pattern)
        return table

    def get_data(self, table: TimeSeriesPrimaryTable, fields) -> ValueType:
        try:
            data = super(TiroTSPump, self).get_data(table, fields=None)
            if not table.meta["only_ts"]:
                if fields:
                    missing_fields = set(f for f in fields if f not in data.keys())
                    if not missing_fields:
                        return data
                else:
                    missing_fields = None
                data |= self.get_data_from_gdb(table, missing_fields)
        except RuntimeError as e:
            if not table.meta["only_ts"]:
                data = self.get_data_from_gdb(table, fields)
            else:
                raise e from e
        return data

    def get_data_from_gdb(self, table: TimeSeriesPrimaryTable, fields) -> ValueType:
        column = table.meta["column"]
        agg_fn = table.meta["agg_fn"]
        pattern = table.meta["pattern"]
        fill_with_default = table.meta["fill_with_default"]
        missing_data = []
        for path, value in self.graph_db_agent.capture_status(
                pattern=pattern,
                flatten=True,
                fill_with_default=fill_with_default,
                skip_telemetry_in_tsdb=True,
        ).items():
            data_point = self.scenario.data_point_path_to_tags(path) | value
            if fields and path.split(PATH_SEP)[-1] not in fields:
                continue
            missing_data.append(data_point)
        index = gen_index(self.config.start, self.config.stop, self.config.step)
        results = {}
        field: str
        if missing_data:
            for field, df in pd.DataFrame(missing_data).groupby("field"):
                series = getattr(df.groupby(column).value, agg_fn)()
                results[field] = pd.DataFrame(data=[series for _ in index], index=index)
        return results

    def capture_status(self, *args, **kwargs):
        return self.graph_db_agent.capture_status(*args, **kwargs)

    def status_as_df(self, pattern=None, fill_with_default=True):
        data = []
        for path, value in self.graph_db_agent.capture_status(
                pattern=pattern,
                flatten=True,
                fill_with_default=fill_with_default,
                skip_telemetry_in_tsdb=False,
        ).items():
            value.pop("timestamp")
            tags = self.scenario.data_point_path_to_tags(path)
            path = PATH_SEP.join(split_path(path)[:-2])
            data_point = dict(asset_path=path, type=tags["type"], field=tags["field"]) | value
            data.append(data_point)
        return pd.DataFrame(data)


