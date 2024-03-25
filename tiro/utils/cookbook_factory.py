import contextlib
import inspect
from copy import copy
from itertools import chain
from pathlib import Path
import re
import logging
from influxdb_client import InfluxDBClient
from tiro.core import Scenario
from tiro.plugins.graph.agent import ArangoAgent
from tiro.plugins.utinni.without_arangodb import TiroTSPump
from utinni import Context, TableBase
from utinni.pump import WrappedDataPump, ConstantTSDataPump
import pandas as pd
import numpy as np


class TablePacker:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __rshift__(self, func):
        return func(*self.args, **self.kwargs)


class TableValuePacker:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __rshift__(self, func):
        runtime = None
        for item in chain(self.args, self.kwargs.values()):
            if isinstance(item, TableBase):
                runtime = item.runtime
                break
        return runtime.make_secondary_table(func, *self.args, **self.kwargs)


class Calculator:
    DEFAULT_SUM_ARGS = {}
    DEFAULT_MEAN_ARGS = {}

    def mean(self, df, **kwargs):
        return df.mean(**self.DEFAULT_MEAN_ARGS, **kwargs)

    def sum(self, df, **kwargs):
        return df.sum(**self.DEFAULT_SUM_ARGS, **kwargs)

    def copy(self, df):
        return df.copy()

    def cal_cooling_load_by_air(self, flow_rate, supply_temp, return_temp):
        return flow_rate * (return_temp - supply_temp) * 1.19 * 1.006 * 1000

    def cal_cooling_load_by_water(self, flow_rate, supply_temp, return_temp):
        return flow_rate * (return_temp - supply_temp) * 4.184 * 997 * 1000

    def cal_rci(self, temp, min_temp=27, max_temp=32):
        return 1 - self.mean(((temp - min_temp) / (max_temp - min_temp)).clip(0))

    def cal_rti(
        self, server_inlet_temp, server_outlet_temp, ac_supply_temp, ac_return_temp
    ):
        return (self.mean(server_outlet_temp) - self.mean(server_inlet_temp)) / (
            self.mean(ac_return_temp) - self.mean(ac_supply_temp)
        )

    def cal_temp_diff(self, supply_temp, return_temp):
        return self.mean(return_temp) - self.mean(supply_temp)

    def cal_mean_flow_temperature(self, flow_rate, temperature):
        return self.sum(flow_rate * temperature) / self.sum(flow_rate)

    def cal_wue(self, pue):
        return pue * 2.4

    def cal_cue(self, pue):
        return pue * 0.408

    def dh_index_from_name(self, name: str) -> int:
        raise NotImplementedError

    def index_dh(self, df):
        if isinstance(df, pd.DataFrame):
            df.columns = df.columns.map(lambda x: self.dh_index_from_name(x))
        elif isinstance(df, pd.Series):
            if isinstance(df.index, pd.MultiIndex):
                df.index = df.index.map(lambda x: (self.dh_index_from_name(x[0]), x[1]))
            else:
                df.index = df.index.map(lambda x: self.dh_index_from_name(x))
        else:
            raise ValueError("Unsupported type.")
        return df

    def online_devices(self, power_df, power_threshold=500):
        if isinstance(power_df, pd.Series):
            return power_df[power_df > power_threshold].index
        elif isinstance(power_df, pd.DataFrame):
            return power_df[power_df > power_threshold].apply(
                lambda x: sorted(x[x > 500].index), axis=1
            )


class CookbookFactoryBase(Calculator):
    SMART_AGG_FN_MAP = {
        "Power": "sum",
        "Temperature": "mean",
        "FlowRate": "sum",
        "ValvePosition": "mean",
        "Pressure": "mean",
        "Humidity": "mean",
        "CoolingCapacity": "sum",
        "COP": "mean",
        "PUE": "mean",
    }

    VALIDATION_DICT = dict(
        CATEGORIES=["dh", "cp", "dc", "task_io"],
        EQUIPMENTS=[
            "acu",
            "ac",
            "ccu",
            "acmv",
            "crac",
            "crah",
            "rack",
            "server",
            "chiller",
            "chilled_water_pump",
            "secondary_chilled_water_pump",
            "primary_chilled_water_pump",
            "condenser_water_pump",
            "cooling_tower",
            "pipe",
            "bypass",
            "riser",
            "floor",
            "room",
            "pdu",
            "pmm",
        ],
        AGGREGATION_FUNCTIONS=["mean", "sum", "total", "min", "max"],
        METRIC_VOCABULARY={
            "ac",
            "air",
            "and",
            "between",
            "capacity",
            "chilled",
            "component",
            "condenser",
            "cooling",
            "cop",
            "cost",
            "cue",
            "current",
            "devices",
            "energy",
            "flow",
            "frequency",
            "humidity",
            "index",
            "inlet",
            "it",
            "load",
            "non",
            "online",
            "outlet",
            "position",
            "power",
            "pressure",
            "pue",
            "rack",
            "rate",
            "rated",
            "ratio",
            "return",
            "room",
            "speed",
            "status",
            "sub",
            "supply",
            "temperature",
            "valve",
            "vsd",
            "water",
            "wue",
        },
    )

    def __init__(
        self,
        scenario_path: Path = Path("scenario/scenario.yaml"),
        uses_path: Path = Path("scenario/uses.yaml"),
        validate_name: bool = True,
    ):
        """
        :param scenario_path: path to scenario.yaml
        :param uses_path: path to uses.yaml
        """
        super().__init__()
        self.scenario = Scenario.from_yaml(scenario_path, uses_path)
        self._config = None
        self._context = None
        self._kwargs = None
        self._table_cache = {}
        self.need_validate_table_name = validate_name

    @property
    def influxdb(self):
        return InfluxDBClient(**self.config.influxdb)

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        self._config = config

    @property
    def context(self):
        return self._context

    @property
    def kwargs(self):
        return self._kwargs

    @kwargs.setter
    def kwargs(self, kwargs):
        self._kwargs = kwargs

    @context.setter
    def context(self, context):
        self._context = context
        self.add_pumps(context)

    def add_pumps(self, context: Context):
        context.add_pump("tiro", TiroTSPump(scenario=self.scenario))
        context.add_pump("wrap", WrappedDataPump())
        context.add_pump("const", ConstantTSDataPump())
        context.add_client(influxdb=self.influxdb)

    def agg_fn_based_on_point_path(self, point_path):
        for k, v in self.SMART_AGG_FN_MAP.items():
            if k in point_path:
                return v
        return "mean"

    def parse_point_path(self, point_path, agg_fn=None):
        if agg_fn is None:
            if "|" in point_path:
                point_path, agg_fn = point_path.split("|", 1)
            else:
                agg_fn = self.agg_fn_based_on_point_path(point_path)
        point_path = point_path.strip()
        agg_fn = agg_fn.strip()
        field = point_path.rsplit("%", 1)[-1].strip()
        groupby = re.search(r"\[(.*?)\]", point_path).group(1)
        if "," in groupby:
            groupby = groupby.split(",")
        key = point_path, agg_fn
        return point_path, field, groupby, agg_fn, key

    def create_table(self, point_path, field, groupby, agg_fn):
        raise NotImplementedError

    def table(self, point_path, agg_fn=None, skip_name_validation=False):
        point_path, field, groupby, agg_fn, key = self.parse_point_path(
            point_path, agg_fn
        )
        if key not in self._table_cache:
            table = self.create_table(point_path, field, groupby, agg_fn)
            if self.need_validate_table_name and skip_name_validation:
                table.set_meta("skip_name_validation", True)
            self._table_cache[key] = table
        return self._table_cache[key]

    t = table

    def wrap(self, data):
        return self.context.wrap_table(data)

    def const(self, data):
        return self.context.const_table(data)

    def all_recipes(self):
        recipes = []
        for name in dir(self):
            if name.startswith("recipes"):
                recipes.append(name)
        return [getattr(self, name) for name in sorted(recipes)]

    @contextlib.contextmanager
    def skip_name_validation(self):
        f = inspect.getouterframes(inspect.currentframe())[2]
        original_table = copy(f.frame.f_locals)
        yield
        for name, table in f.frame.f_locals.items():
            if isinstance(table, TableBase) and name not in original_table:
                table.set_meta("skip_name_validation", True)

    def validate_table_name(self, name):
        try:
            category, equipment, metric, *suffix = name.split("__")
        except ValueError:
            category, metric, *suffix = name.split("__")
            equipment = None
        suffix = "_".join(suffix)
        if suffix not in ("", "i"):
            logging.warning(f"Invalid suffix: {suffix}")
            return False
        if category not in self.VALIDATION_DICT["CATEGORIES"]:
            logging.warning(f"Invalid category: {category}")
            return False
        if equipment and equipment not in self.VALIDATION_DICT["EQUIPMENTS"]:
            logging.warning(f"Invalid equipment: {equipment}")
            return False
        for prefix in self.VALIDATION_DICT["AGGREGATION_FUNCTIONS"]:
            metric = metric.removeprefix(f"{prefix}_")
        for word in metric.split("_"):
            if word not in self.VALIDATION_DICT["METRIC_VOCABULARY"]:
                logging.warning(f"Invalid word: {word}")
                return False
        return True

    def validate_tables(self, tables):
        if not self.need_validate_table_name:
            return
        for name, table in tables.items():
            if isinstance(table, TableBase):
                if table.meta.get("skip_name_validation", False):
                    continue
                if not self.validate_table_name(name):
                    raise ValueError(f"Invalid table name: {name}")

    def reset(self):
        self._table_cache.clear()
        self._config = None
        self._context = None
        self._kwargs = None

    def __call__(self, context: Context, config, **kwargs):
        self.reset()
        self.config = config
        self.context = context
        self.kwargs = kwargs
        for recipes in self.all_recipes():
            tables = recipes()
            self.validate_tables(tables)
            self.context.collect(tables, clear_existing=False)

    def __getattr__(self, item):
        return getattr(self.context, item)

    def dh_index_from_name(self, name: str):
        return 0


class StatusCookbookFactory(CookbookFactoryBase):
    DEFAULT_SUM_ARGS = {}
    DEFAULT_MEAN_ARGS = {}

    def __init__(
        self,
        scenario_path: Path = Path("scenario/scenario.yaml"),
        uses_path: Path = Path("scenario/uses.yaml"),
        max_time_buffer: int = 3600,
    ):
        """
        :param scenario_path: path to scenario.yaml
        :param uses_path: path to uses.yaml
        :param max_time_buffer: maximum time buffer for status query
        """
        super().__init__(scenario_path=scenario_path, uses_path=uses_path)
        self.max_time_buffer = max_time_buffer

    def create_table(self, point_path, field, groupby, agg_fn):
        extra_options = dict(
            type="status",
            column=groupby,
            time_agg_fn="mean",
            asset_agg_fn=agg_fn,
            max_time_diff=self.max_time_buffer,
        )
        if agg_fn == "sum":
            extra_options["asset_agg_fn_kwargs"] = {"min_count": 1}
        return self.context.tiro_table(point_path, **extra_options)[field]

    def aggregate_component_power(self, **kwargs):
        return self.context.aggregate(
            *[self.sum(table).set_name(name) for name, table in kwargs.items()]
        )


class HistorianCookbookFactory(CookbookFactoryBase):
    DEFAULT_SUM_ARGS = dict(axis=1, min_count=1)
    DEFAULT_MEAN_ARGS = dict(axis=1)
    HEALTH_INDICATOR = NotImplemented

    def create_table(self, point_path, field, groupby, agg_fn):
        extra_options = dict(
            type="historian", column=groupby, time_agg_fn="mean", asset_agg_fn=agg_fn
        )
        if agg_fn == "sum":
            extra_options["asset_agg_fn_kwargs"] = {"min_count": 1}
        return self.context.tiro_table(point_path, **extra_options)[field]

    def cal_power_to_energy(self, power):
        return power * power.index.to_series().diff().dt.total_seconds().bfill() / 3600

    def cal_energy_to_cost(self, energy):
        return energy * self.kwargs.get("tariff", 0.3)

    def cal_power_to_cost(self, power):
        return self.cal_energy_to_cost(self.cal_power_to_energy(power))

    def __call__(self, *args, **kwargs):
        super().__call__(*args, **kwargs)
        if self.HEALTH_INDICATOR is not NotImplemented:
            table = getattr(self.context, self.HEALTH_INDICATOR)
            self.context.define(
                "health_indicator", table.replace(np.nan, 0).astype(bool).astype(int)
            )
