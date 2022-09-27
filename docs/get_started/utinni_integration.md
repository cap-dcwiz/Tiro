# Utinni Integration

???+ attention "Utinni"

    [Utinni](https://github.com/cap-dcwiz/Utinni) is in a private repository; thus, it is not included in the dependencies of this project. You will need to install it separately. 

    There is a pre-compilled wheel file in `/deps` directory. You can install it by running the following command:
    
    ```console
    $ pip install deps/utinni-*.whl
    ```

    Or, you can add Utinni into your project dependencies.
    
    For more information, please refer to [https://github.com/cap-dcwiz/Utinni](https://github.com/cap-dcwiz/Utinni) for more information. Or contact us directly.

!!! attention 

    Please also refer to [Utinni](https://github.com/cap-dcwiz/Utinni) for the concepts and usages of Utinni. This section will assume that you have already known the basic concepts of Utinni.

Tiro is designed to be integrated with [Utinni](https://github.com/cap-dcwiz/Utinni). An Utinni pump has been provided to access the data collected and managed by Tiro, following the unified data model defined by the scenario and uses files.

In this section, we show how to use Utinni-based data tools to access the data collected by the workflow in [last section](./karez_integration.md).

## Data Pump

Tiro provides a data pump that can extract tiro-collected data from InfluxDB and ArangoDB and organise them according to the scenario created.

```pycon
>>> from pathlib import Path
>>> from datetime import timedelta
>>> from utinni import Context
>>> from tiro.core import Scenario
>>> from tiro.plugins.utinni import TiroTSPump
>>>
>>> # Define the pump
>>> scenario = Scenario.from_yaml(Path("scenario/scenario.yaml"),
>>>                               Path("scenario/use-srv1.yaml"), Path("scenario/use-srv2.yaml"))
>>> pump = TiroTSPump(
>>>     scenario=scenario,
>>>     influxdb_url="http://localhost:8086",
>>>     influxdb_token="tiro-token",
>>>     influxdb_org="tiro",
>>>     arangodb_db = "tiro",
>>>     arangodb_graph = "scenario",
>>>     arangodb_hosts = "http://localhost:8529",
>>>     arangodb_auth=dict(password="tiro-password")
>>> ).bind(
>>>     influxdb_bucket="tiro",
>>>     influxdb_measurement="tiro_telemetry"
>>> )
>>>
>>> # Create a context and add the pump to it
>>> context = Context()
>>> context.add_pump("tiro", pump)
```

Then, we can define `tiro_table`s. There are two types of tiro tables. One is for time-series, or historian, data, and the other is for status data.

## Query Historian Data

The historian table can be created by passing `type="historian"` to the table constructor. 

```pycon
>>> rack_power = context.tiro_table(
>>>     "%%Rack%ActivePower", 
>>>     type="historian",
>>>     column="Rack", 
>>> )["ActivePower"]
```

Later, we can bind a time period to context (or pump, table) and access its real value.

```pycon
>>> context.bind(
>>>     start=-timedelta(hours=1),
>>>     step=timedelta(minutes=5)
>>> )
>>> rack_power.value
                           rack_0  rack_1
2022-09-27 15:00:00+08:00  583.51  124.94
2022-09-27 15:05:00+08:00  240.44  670.64
2022-09-27 15:10:00+08:00  152.52  999.12
2022-09-27 15:15:00+08:00  866.90  969.20
2022-09-27 15:20:00+08:00  554.68  357.52
2022-09-27 15:25:00+08:00   38.95  897.61
2022-09-27 15:30:00+08:00  350.29  580.90
2022-09-27 15:35:00+08:00  284.33  167.15
2022-09-27 15:40:00+08:00  816.69  758.66
2022-09-27 15:45:00+08:00  260.58  320.97
2022-09-27 15:50:00+08:00  360.74  735.50
2022-09-27 15:55:00+08:00  908.48  221.26
2022-09-27 16:00:00+08:00   48.59  830.35
```

Or, we can create a table to directly calculate the mean flow rate of servers on each rack.

```pycon
>>> rack_flow = context.tiro_table(
>>>     "%%Server%FlowRate", 
>>>     type="historian",
>>>     column="Rack", 
>>>     asset_agg_fn="sum"
>>> )["FlowRate"]
>>> rack_flow.value
                            rack_0   rack_1
2022-09-27 15:10:00+08:00  2314.28  1595.97
2022-09-27 15:15:00+08:00  1684.89   725.40
2022-09-27 15:20:00+08:00  1704.01  1146.60
2022-09-27 15:25:00+08:00  2469.59   888.24
2022-09-27 15:30:00+08:00  1484.55  1831.56
2022-09-27 15:35:00+08:00  1395.31  1706.43
2022-09-27 15:40:00+08:00  1489.70  1741.37
2022-09-27 15:45:00+08:00  1842.68  1008.99
2022-09-27 15:50:00+08:00  1593.35  1911.79
2022-09-27 15:55:00+08:00  1888.52   999.81
2022-09-27 16:00:00+08:00  1587.14  2006.45
2022-09-27 16:05:00+08:00  1752.09  1323.92
2022-09-27 16:10:00+08:00  1629.37  1596.03
```

## Query Status Data

The status table can be created by passing `type="status"` to the table constructor. This table contains the latest values of data points instead of time-series data.

For example, the following code creates a table to query the active power of all assets that have such data points

```pycon
>>> power_status = context.tiro_table(
>>>     "%%ActivePower",
>>>     type="status", 
>>>     value_only=True,
>>> )
>>> power_status.value
{
    'DataHall': {
        'data_hall_0': {
            'CRAC': {'crac_0': {'Telemetry': {'ActivePower': 57.83}}},
            'Rack': {
                'rack_0': {'Telemetry': {'ActivePower': 955.42}},
                'rack_1': {'Telemetry': {'ActivePower': 600.6}}
            }
        }
    }
}
```

Note that by default, the "status" table are free-from tables, whole values are dictionaries. If we want the data been converted to a pandas dataframe, we can pass `as_dataframe=True` to the table constructor.

```pycon 
>>> power_table = context.tiro_table(
>>>     "%%FlowRate",
>>>     type="status", 
>>>     as_dataframe=True,
>>>     include_tags=["Rack", "Server"],
>>>     value_only=True,
>>> )["FlowRate"]
>>> power_table.value
     Rack    Server   value
0  rack_0  server_0  876.44
1  rack_0  server_1  443.27
2  rack_0  server_2  369.87
3  rack_1  server_3  535.70
4  rack_1  server_4  476.11
5  rack_1  server_5  160.21
```

!!! Info
    
    Please also refer to the Tiro Query Guide for more explainations on how to query data from Tiro.
