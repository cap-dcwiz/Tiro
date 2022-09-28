# Glossary

`Entity`, `Asset`
:   A `Entity` or a `Asset` is a device, equipment or virtual group in an IoT environment. An entity can have several child entities.

`Data Point`
:   A *telemetry* or *attribute* of the asset.

`Telemetry`
:   A `Telemetry` is a data point that can be measured or observed. It is a time series data point that changes over time.

`Attribute`
:   A `Attribute` is a data point that represents the state or characteristic of the asset. It is a static data point.

`Scenario`
:   A `Scenario` contains a set of assets and their relations. The assets are organized in a tree structure.

`Uses`
:   A `Uses` file contains a set of data points that are required by a use case. The data points are assigned to the assets in the scenario.

`Schema`
:   A [JSON schema](https://json-schema.org/) to describe the scenario and the information of data points required by multiple use cases.

`Asset Path`
:   A path to an asset or a data point in the scenario. The path is a list of asset types and names from the root asset to the target asset. For example, an asset with path `"DataHall.data_hall.Rack.rack_1.Server.server_1"` is the server named `server_1` in a rack named `rack_1` in a data hall named `data_hall`. And the data point with path `"DataHall.data_hall.Rack.rack_1.Server.server_1.Telemetry.temperature"` is the temperature telemetry of the server named `server_1` in a rack named `rack_1` in a data hall named `data_hall`. In some occasions, the `Telemetry` or `Attribute` before the data point name can be omitted.

`Type Path`
: `Asset Path` without asset and data point types. For example, the type path of the asset with path `"DataHall.data_hall.Rack.rack_1.Server.server_1"` is `"DataHall.Rack.Server"`.
