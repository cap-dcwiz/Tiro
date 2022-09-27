# Create Scenario

Scenario defines the hierarchy of the assets and the relationships between them. It is a tree structure where each node is an asset and each edge is a relationship between two assets. 

## Scenario

The first step to use **Tiro** is to define the scenario. The scenario is defined in a YAML file. Let's define a simple scenario 

=== "scenario.yaml"

    ```yaml
    DataHall:
      $number: 1
      $type: DataHall
      Rack:
        $number: 2
        $type: Rack
        Server:
          $number: 2-5
          $type: Server
      CRAC:
        $number: 1
        $type: CRAC
    ```

This file defines a scenario of data that contains two racks and 1 CRAC, and each rack contains 2-5 servers. The `$asset_library_name` is the name of the asset library that contains the asset types. The `$number` is the number of assets of the same type. The `$type` is the type of the asset, which should be a name of a `Entity` class defined in the asset library. 


## Asset Library

Let's define a simple asset library. This step is optional and should be able to reuse for different scenarios.

=== "tiro_assets.py"

    ```python
    from functools import partial

    from faker import Faker
    from pydantic import confloat

    from tiro.core import Entity
    from tiro.core.model import Telemetry

    default_faker = Faker()


    def RangedFloatTelemetry(
        ge, le, unit=None, right_digits=2, faker=default_faker
    ) -> Telemetry:
        return Telemetry(
            confloat(ge=ge, le=le),
            unit,
            faker=partial(
                faker.pyfloat, right_digits=right_digits, 
                min_value=ge, max_value=le
            ),
        )


    class DataHall(Entity):
        """Data hall asset."""
        RoomTemperature = RangedFloatTelemetry(-50, 50)
        ChilledWaterSupplyTemperature = RangedFloatTelemetry(0, 1000)
        ChilledWaterReturnTemperature = RangedFloatTelemetry(0, 1000)


    class Rack(Entity):
        ActivePower: RangedFloatTelemetry(0, 1000)
        FrontTemperatures: RangedFloatTelemetry(0, 60)
        BackTemperature: RangedFloatTelemetry(0, 60)
        Temperature: RangedFloatTelemetry(0, 60)


    class Server(Entity):
        ActivePower: RangedFloatTelemetry(0, 1000)
        HeatLoad: RangedFloatTelemetry(0, 1000)
        FlowRate: RangedFloatTelemetry(0, 1000)
        CPUTemperature: RangedFloatTelemetry(0, 150)


    class CRAC(Entity):
        ActivePower: RangedFloatTelemetry(0, 1000)
        SupplyTemperature: RangedFloatTelemetry(0, 50)
        ReturnTemperature: RangedFloatTelemetry(0, 50)
        FanSpeed: RangedFloatTelemetry(0, 1000)
    ```

???+ info "Tiro-asset-library"

    For DCWiz project, we have pre-defined an asset library that contains common assets and data points in a data center. You can find it in the [tiro-assets](https://github.com/cap-dcwiz/Tiro-asset-library) repository.

After defining the asset library, let's declare the library name and path in the scenario file. 

=== "scenario.yaml"

    ```yaml hl_lines="1 2"
    $asset_library_name: test_assets
    $asset_library_path: ./

    DataHall:
      $number: 1
      $type: DataHall
      Rack:
        $number: 2
        $type: Rack
        Server:
          $number: 2-5
          $type: Server
      CRAC:
        $number: 1
        $type: CRAC
    ```


The defined scenario can be shared among different applications or services. However, to actually use the scenario, each application or service still needs to declare the data points it wants in a "use" file, the data points declared must have been defined in the asset library. For example, one can declare active power, supply temperature, return temperature or fan speed for CRAC, or heat load, flow rate or CPU temperature for server. The use file is also a YAML file.


## Uses

Now, let's define two use files for service "srv1" and "srv2", respectively. Assume that srv1 pays more attentions to the power consumption of the data center, while srv2 cares more about the cooling performance of the data center.

=== "use-srv1.yaml"

    ```yaml
    - DataHall:
      - CRAC:
        - ActivePower
      - Rack:
        - ActivePower
    ```


=== "use-srv2.yaml"

    ```yaml
    - DataHall:
      - Rack:
        - ChilledWaterSupplyTemperature
        - ChilledWaterReturnTemperature
        - Server:
          - FlowRate
      - CRAC:
        - SupplyTemperature
        - ReturnTemperature
    ```

## Test

Now, we can test our scenario, asset library and use files. Let's try to generate an example snapshot of the scenario.

```console
$ tiro schema example -c scenario.yaml use-srv1.yaml use-srv2.yaml -o example.json
```

We should see similar context in a `example.json` file. There should be generated data for all the data points declared in both uses files.

=== "example.json"

    ```json
    {
      "DataHall": {
        "data_hall_0": {
          "CRAC": {
            "crac_0": {
              "ReturnTemperature": 26.47,
              "SupplyTemperature": 36.29,
              "ActivePower": 745.14
            }
          },
          "Rack": {
            "rack_0": {
              "Server": {
                "server_0": {
                  "FlowRate": 116.64
                },
                "server_1": {
                  "FlowRate": 673.49
                },
                "server_2": {
                  "FlowRate": 190.28
                },
                "server_3": {
                  "FlowRate": 533.99
                },
                "server_4": {
                  "FlowRate": 917.35
                }
              },
              "ActivePower": 63.23
            },
            "rack_1": {
              "Server": {
                "server_5": {
                  "FlowRate": 739.63
                },
                "server_6": {
                  "FlowRate": 65.5
                }
              },
              "ActivePower": 913.24
            }
          }
        }
      }
    }
    ```