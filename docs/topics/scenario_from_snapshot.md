# Drafting Scenario from Snapshot

In [Get Started](../get_started/index.md), we create a scenario from scratch. However, it can still be tedious. Therefore, Tiro also provides tools to help you draft the scenario and uses files from a "snapshot" of the system.

## Snapshot

A "snapshot" is a csv file that contains the list of data points and their values at a specific time, which may be exported from a system by some external tools. The csv file must include the following columns:

* `data_point`: the name of the data point, like "temperature" or "pressure";
* `asset`: the name of the asset that contains the data point, like "room1" or "rack1";
* `asset_type`: the type of the asset, like "Room" or "Rack";
* `parent_asset`: the name of the parent asset, for example, the parent asset of "rack1" may be "room1", as "rack1" is installed in "room1";
* `value`: the value of the data point, like "23.5" or "true".

and an optional column `uuid`, which is the unique identifier of the data point. If the `uuid` column is not provided, Tiro will generate a UUID for each data point using the `asset` and `data_point` columns.

Below is the content of an example snapshot file `snapshot.csv`:

???+ example "snapshot.csv"

    | data\_point        | asset      | asset\_type | parent\_asset | value |
    | ------------------ | ---------- | ----------- | ------------- | ----- |
    | Supply Temperature | crac\_1    | CRAC        | data\_hall    | 15    |
    | Supply Temperature | crac\_2    | CRAC        | data\_hall    | 17    |
    | Supply Temperature | crac\_3    | CRAC        | data\_hall    | 16.5  |
    | Supply Temperature | crac\_4    | CRAC        | data\_hall    | 15    |
    | CPU Temperature    | server\_1  | Server      | rack          | 80    |
    | CPU Temperature    | server\_2  | Server      | rack          | 60    |
    | CPU Temperature    | server\_3  | Server      | rack          | 67    |
    | CPU Temperature    | server\_4  | Server      | rack          | 55    |
    | Active Power       | rack       | Rack        | data\_hall    | 10000 |
    | Active Power       | crac\_1    | CRAC        | data\_hall    | 3000  |
    | Active Power       | crac\_2    | CRAC        | data\_hall    | 4000  |
    | Active Power       | crac\_3    | CRAC        | data\_hall    | 6000  |
    | Active Power       | crac\_4    | CRAC        | data\_hall    | 4300  |
    | Temperature        | data\_hall | DataHall    |               | 23    |

## Drafting Scenario

With the snapshot file, we can draft the scenario by running the following command:

```console
$ tiro draft scenario snapshot.csv -o scenario_draft.yaml
```

The resulting scenario draft file `scenario_draft.yaml` will be like:

=== "scenario_draft.yaml"

    ```yaml
    DataHall:
      $number: 1
      $type: DataHall
      CRAC:
        $number: 4
        $type: CRAC
      Rack:
        $number: 1
        $type: Rack
        Server:
          $number: 4
          $type: Server
    ```

Then, we can edit the scenario draft file to add more details, like correcting the type of the data points and adding the asset library name or path.


## Drafting Uses File

Run the following command to draft the uses file:

```console
$ tiro draft uses snapshot.csv -o uses.yaml
```

The resulting uses draft file `uses.yaml` will be like:

=== "uses_draft.yaml"

    ```yaml
    - DataHall:
      - CRAC:
        - ActivePower
        - SupplyTemperature
      - Rack:
        - ActivePower
        - Server:
          - CPUTemperature
      - Temperature
    ```

The files can then be distributed to different service or application developers, and each developer can delete the data points that are not needed. 

## Drafting Reference File

Additional, to better mimic the real system, Tiro also supports to appoint a reference file when generating mock data. The reference file contains the real asset names and relations, reference values of the data points and some additional information. So, when this file is provided, the mock data generator will try to follow the actual assets and value ranges in the reference file to make the generated data more realistic.

Tiro also provides a command to draft the reference file from the snapshot file:

```console
$ tiro draft reference snapshot.csv -o reference.yaml
```

=== "reference.yaml"

    ```yaml
    tree:
      DataHall:
        data_hall:
          CRAC:
            crac_1:
              DataPoints:
              - SupplyTemperature
              - ActivePower
            crac_2:
              DataPoints:
              - SupplyTemperature
              - ActivePower
            crac_3:
              DataPoints:
              - SupplyTemperature
              - ActivePower
            crac_4:
              DataPoints:
              - SupplyTemperature
              - ActivePower
          DataPoints:
          - Temperature
          Rack:
            rack:
              DataPoints:
              - ActivePower
              Server:
                server_1:
                  DataPoints:
                  - CPUTemperature
                server_2:
                  DataPoints:
                  - CPUTemperature
                server_3:
                  DataPoints:
                  - CPUTemperature
                server_4:
                  DataPoints:
                  - CPUTemperature
    uuid_map:
      crac_1.ActivePower: DataHall.data_hall.CRAC.crac_1.ActivePower
      crac_1.SupplyTemperature: DataHall.data_hall.CRAC.crac_1.SupplyTemperature
      crac_2.ActivePower: DataHall.data_hall.CRAC.crac_2.ActivePower
      crac_2.SupplyTemperature: DataHall.data_hall.CRAC.crac_2.SupplyTemperature
      crac_3.ActivePower: DataHall.data_hall.CRAC.crac_3.ActivePower
      crac_3.SupplyTemperature: DataHall.data_hall.CRAC.crac_3.SupplyTemperature
      crac_4.ActivePower: DataHall.data_hall.CRAC.crac_4.ActivePower
      crac_4.SupplyTemperature: DataHall.data_hall.CRAC.crac_4.SupplyTemperature
      data_hall.Temperature: DataHall.data_hall.Temperature
      rack.ActivePower: DataHall.data_hall.Rack.rack.ActivePower
      server_1.CPUTemperature: DataHall.data_hall.Rack.rack.Server.server_1.CPUTemperature
      server_2.CPUTemperature: DataHall.data_hall.Rack.rack.Server.server_2.CPUTemperature
      server_3.CPUTemperature: DataHall.data_hall.Rack.rack.Server.server_3.CPUTemperature
      server_4.CPUTemperature: DataHall.data_hall.Rack.rack.Server.server_4.CPUTemperature
    value_range:
      DataHall.CRAC.ActivePower:
        max: 6000.0
        min: 3000.0
      DataHall.CRAC.SupplyTemperature:
        max: 17.0
        min: 15.0
      DataHall.Rack.ActivePower:
        max: 10000.0
        min: 10000.0
      DataHall.Rack.Server.CPUTemperature:
        max: 80.0
        min: 55.0
      DataHall.Temperature:
        max: 23.0
        min: 23.0
    ```

Having the reference file, we can generate more realistic mock data with the following command:

```console
$ tiro mock serve scenario.yaml use-srv1.yaml use-srv2.yaml -r reference.yaml
```
