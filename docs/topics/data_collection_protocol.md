# Date Collection Protocol

In [Get Started](../get_started/index.md), we build a data collection that retrieves data from a mocking service. In real system, we just need to replace the mocking service with the real data collector, aka. the Karez dispatcher and connector roles. The Karez connector can be easily integrated into the workflow as long as it follows the data collection protocol.

## Data Collection Protocol

There are two kinds of data formats that a Karez connector can send to NATS queue:

### By Path

 A Path is a string like `DataHall.datahall_0.Rack.rack_0.Server.server_0.CPUTemperature`, which encodes the path of the data point from the root asset to the data point, separated by `.`. This can be used to locate the data point in the scenario. 

The first data format is a JSON object with the following fields:

```json
{
   "path":"DataHall.data_hall_0.CRAC.crac_0.Telemetry.SupplyTemperature",
   "result":{
      "value":9.31,
      "timestamp":"2022-09-28T11:06:35.050694"
   },
   "_karez":{
      "category":"telemetry"
   }
}
```

If a Karez connector sends such data to the NATS queue, it can be directly pipelined to a `TiroPreprocessConverter` and following tasks.

!!! Note

    The `_karez` field is reserved for internal use. It is used to indicate the category of the data point, which can be `telemetry` or `attribute`. The `telemetry` category is used for data points that can be continuously updated, like temperature, pressure, etc. The `attribute` category is used for data points that can only be updated once, like the status of a switch, the status of a door, etc. This filed can be omitted. If omitted, the data point will be treated as a `telemetry` data point.

### Py ID

The second data format is a simple JSON format with only two fields `name` and `value`. This format may be more convenient for some data collectors, like the OPC-UA connector. In realistic scenarios, the data collector may be a third-party system, which may not be able to provide the path of the data point. In this case, the data collector can provide the `name` of the data point, which is the unique identifier of the data point in the scenario. The `value` field is the value of the data point.

```json
{
   "name":"some_uuid",
   "value":9.31
}
```

If use this case, another `TiroUpdateInfoForValueConverter` converter needs to be added before `TiroPreprocessConverter` to add more metadata to the data point. A sample configuration of this converter is as follows:

```yaml
converters:
  - type: tiro_update_info_for_value
    reference: scenario/reference.yaml
    scenario: scenario/scenario.yaml
    uses: scenario/uses.yaml
    tz_infos:
      SGT: Aisa/Singapore
    next:
      - tiro_preprocess
      - update_category_for_validator
```

Note that it needs and additional `reference.yaml` file to provide the mapping from the `name` to the path of the data point. Please refer to [this section](./scenario_from_snapshot.md#drafting-reference-file) for more information.