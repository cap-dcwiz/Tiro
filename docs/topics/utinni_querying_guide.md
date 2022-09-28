# Query Guide

This guide explains how to query data from using Tiro-provided Utinni data pump in more details.

## Query String

The most common way to query data is to use the query string. The query string is a string to match the "type path" of the data point. The "type path" is the path to the data point in the scenario tree, but includes only the asset type names but no asset names. For example, the "type path" of the data point `DataHall.data_hall.CRAC.crac_1.Telemetry.SupplyTemperature` is `DataHall.CRAC.SupplyTemperature`.

A query string is basically a regular expression. However, because `.` is a special character in regular expression, we use `%` to represent `.` in the query string. For example, the query string `DataHall%CRAC%SupplyTemperature` matches the data point `DataHall.CRAC.SupplyTemperature`. Also, we introduce `%%` to match any number of characters including `.`. For example, the query string `DataHall%%Temperature` matches the data point `DataHall.CRAC.SupplyTemperature` and `DataHall.Rack.CPUTemperature`.

The table definition of the Tiro Pump has a unified interface

```python
context.tiro_table(query_str, type, **kwargs)
```
where `query_str` is the query string, and type can be `historian` or `status`.

## Querying Historian Data

When passing `type="historian"` to the table constructor, the table will query historian data. The table will always be "3-D" table, that is, the value is a dictionary of `pandas.DataFreame` indexed by the timestamp. The keys of the dictionary are the data point names. The columns of the `pandas.DataFreame` are the data point names. For example, the following query will return a dictionary of two tabels.

```pycon
>>> context.bind(start=-timedelta(hours=1), step=timedelta(minutes=30))
>>> context.tiro_table("%%CRAC%%Temperature", type="historian").value
{
    'ReturnTemperature':                            DataHall.data_hall_0.CRAC.crac_0
2022-09-28 12:30:00+08:00                               NaN
2022-09-28 13:00:00+08:00                             46.85
2022-09-28 13:30:00+08:00                             43.84,
    'SupplyTemperature':                            DataHall.data_hall_0.CRAC.crac_0
2022-09-28 12:30:00+08:00                               NaN
2022-09-28 13:00:00+08:00                             45.52
2022-09-28 13:30:00+08:00                              1.42
}
```

There is an additional parameter `column` can be passed to the table constructor, which can be `"asset_path"` or a asset type like `"Rack"`. By default, it is `asset_path`, which means the full path of the data point, like `DataHall.data_hall.CRAC.crac_1.Telemetry.SupplyTemperature`. In this case the returned dataframe's column will be the full path of the data point. Otherwise, if `column` is set to an asset type, the name of the asset of the appointed type which relates to the data point will be used as the column name. For example, if `column` is set to `"Rack"`, and the query string is `%%Rack%ActivePower`, the returned data frame will be a dataframe whose column is different rack names, and the value is corresponding active powers

When passing the `column` parameter, if there are multiple columns which have the same name, they will be aggregated, and the aggregation function and additional keyword arguments can be passed to the table constructor by `asset_agg_fn` and `asser_agg_fn_kwargs`, respectively. For example, the following query will return total flow rate of each rack. The default aggregation function is `mean`, and the default aggregation function keyword arguments is `{}`.

```pycon
>>> context.bind(start=-timedelta(hours=1), step=timedelta(minutes=30))
>>>     context.tiro_table(
>>>         "%%Rack%%FlowRate", 
>>>         type="historian",
>>>         column="Rack",
>>>         asset_agg_fn="sum",     
>>>     )["FlowRate"].value
                            rack_0   rack_1
2022-09-28 12:30:00+08:00     0.00     0.00
2022-09-28 13:00:00+08:00  2150.16  2649.47
2022-09-28 13:30:00+08:00  1922.42  1848.53
```

## Querying Status Data

When passing `type="status"` to the table constructor, the table will query status data. Additional parameter `as_data_frame` can be passed to the table constructor, which can be `True` or `False`. By default, it is `False`. In this case, the returned table will contain an embedded table. If `as_data_frame` is set to `True`, Tiro will try to convert the embedded table to a `pandas.DataFreame`. 

```pycon
>>> context.tiro_table(
>>>     "%%ActivePower",
>>>     type="status",
>>>     as_dataframe=False,
>>> ).value
{
    'DataHall': {
        'data_hall_0': {
            'CRAC': {
                'crac_0': {
                    'Telemetry': {'ActivePower': {'timestamp': 1664344487.591439, 'unit': None, 'value': 665.63}}
                }
            },
            'Rack': {
                'rack_0': {
                    'Telemetry': {'ActivePower': {'timestamp': 1664344487.941468, 'unit': None, 'value': 648.4}}
                },
                'rack_1': {
                    'Telemetry': {'ActivePower': {'timestamp': 1664344487.672051, 'unit': None, 'value': 575.49}}
                }
            }
        }
    }
}
>>> context.tiro_table(
>>>     "%%ActivePower",
>>>     type="status",
>>>     as_dataframe=True,
>>> )["ActivePower"].value
{
    'ActivePower':                                                        path     DataHall  \
asset_path                                                                 
DataHall.data_hall_0.CRAC.crac_0  DataHall.CRAC.ActivePower  data_hall_0   
DataHall.data_hall_0.Rack.rack_0  DataHall.Rack.ActivePower  data_hall_0   
DataHall.data_hall_0.Rack.rack_1  DataHall.Rack.ActivePower  data_hall_0   

                                    CRAC       type     timestamp  unit  \
asset_path                                                                
DataHall.data_hall_0.CRAC.crac_0  crac_0  Telemetry  1.664345e+09  None   
DataHall.data_hall_0.Rack.rack_0     NaN  Telemetry  1.664345e+09  None   
DataHall.data_hall_0.Rack.rack_1     NaN  Telemetry  1.664345e+09  None   

                                   value    Rack  
asset_path                                        
DataHall.data_hall_0.CRAC.crac_0  115.49     NaN  
DataHall.data_hall_0.Rack.rack_0  656.66  rack_0  
DataHall.data_hall_0.Rack.rack_1  198.19  rack_1  
}
```

There is also a parameter `value_only` can be passed to the table constructor, which can be `True` or `False`. By default, it is `False`. If it is `True`, the timestamp and unit information will be removed from the returned table. 

```pycon
>>> context.tiro_table(
>>>     "%%ActivePower",
>>>     type="status",
>>>     as_dataframe=False,
>>>     value_only=True,
>>> ).value
{
    'DataHall': {
        'data_hall_0': {
            'CRAC': {'crac_0': {'Telemetry': {'ActivePower': 469.97}}},
            'Rack': {
                'rack_0': {'Telemetry': {'ActivePower': 926.17}},
                'rack_1': {'Telemetry': {'ActivePower': 924.3}}
            }
        }
    }
}
>>> context.tiro_table(
>>>     "%%ActivePower",
>>>     type="status",
>>>     as_dataframe=True,
>>>     value_only=True
>>> )["ActivePower"].value
                                                       path     DataHall  \
asset_path                                                                 
DataHall.data_hall_0.CRAC.crac_0  DataHall.CRAC.ActivePower  data_hall_0   
DataHall.data_hall_0.Rack.rack_0  DataHall.Rack.ActivePower  data_hall_0   
DataHall.data_hall_0.Rack.rack_1  DataHall.Rack.ActivePower  data_hall_0   

                                    CRAC       type   value    Rack  
asset_path                                                           
DataHall.data_hall_0.CRAC.crac_0  crac_0  Telemetry   51.80     NaN  
DataHall.data_hall_0.Rack.rack_0     NaN  Telemetry  698.57  rack_0  
DataHall.data_hall_0.Rack.rack_1     NaN  Telemetry  109.14  rack_1
```

Also, when `as_dataframe=True`, there is an additional parameter `include_tags` can be passed to the table constructor. By default, it is `all`, which means the return dataframe will include as much information as possible, as shown in above example. If `include_tags` is set to an asset type or a list of asset types, the columns will be filtered to only include the specified asset types. For example, 

```pycon
>>> context.tiro_table(
>>>     "%%FlowRate",
>>>     type="status",
>>>     as_dataframe=True,
>>>     include_tags=["Rack", "Server"],
>>>     value_only=True
>>> )["FlowRate"].value
     Rack    Server   value
0  rack_0  server_0  527.90
1  rack_0  server_1  597.79
2  rack_0  server_2  587.88
3  rack_0  server_3  863.72
4  rack_1  server_3  863.72
5  rack_1  server_4  590.90
6  rack_1  server_5  865.13
7  rack_1  server_6  357.40
8  rack_1  server_7  125.10
```

### More Complex Status Query

When querying status data, other than using the simple query string, one can also pass in a more complex dictionary (or a yaml file containing the dictionary) to achieve more complex query. Here is an example.

```pycon
>>> query="""
>>> DataHall:
>>>   Rack:
>>>     $name_match: _1
>>>     Server:
>>>       FlowRate:
>>>         $lt: 400
>>>   CRAC:
>>>     ActivePower:
>>>     _ReturnTemperature: #
>>>       $lt: 15
>>>       $gt: 25
>>> """
>>> query_dict = yaml.safe_load(query)
>>> context.tiro_table(
>>>     yaml.safe_load(query),
>>>     type="status",
>>>     value_only=True
>>> ).value
{
    'DataHall': {
        'data_hall_0': {
            'Rack': {
                'rack_1': {
                    'Server': {
                        'server_3': {'Telemetry': {'FlowRate': 468.75}},
                        'server_5': {'Telemetry': {'FlowRate': 892.7}},
                        'server_6': {'Telemetry': {'FlowRate': 903.21}},
                        'server_7': {'Telemetry': {'FlowRate': 879.9}}
                    }
                }
            },
            'CRAC': {'crac_0': {'Telemetry': {'ActivePower': 732.24}}}
        }
    }
}
```

The above example queries the servers' current flow rates and CRACs' active powers at the same time, but

1. Only considers the servers in the racks whose names contain `_1` (in our case, only "rack_1");

2. Only considers the servers whose flow rates are less than 400;

3. Only considers the CRACs whose return temperatures are between 15 and 25.

!!! note

    1. Available filters:

        * `$name_match`: match the asset name with the given regex pattern. 

        * `$lt`, `$le`, `$gt`, `$ge`: compare the value with the given number.

        * `$match`, `$not_match`: match the string value with the given regex pattern.

    2. The data point name starts with `_` will not be included in the returned data, but they can be used to filter the data points.
