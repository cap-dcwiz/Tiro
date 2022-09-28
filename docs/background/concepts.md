# Background

## Why Tiro?



## Workflow

![Tiro Architecture](tiro%20concepts.svg)

## Glossary

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

## Materials

### Slides

* [DCWiz Data Workflow](dcwiz_data_workflow.pdf)
* [DCWiz Data Modules](dcwiz_data_modules.pdf)

### Related Projects:

* [Utinni](https://github.com/cap-dcwiz/Utinni)
* [Karez](https://github.com/cap-dcwiz/Karez)
* [Tiro-asset-library](https://github.com/cap-dcwiz/Tiro-asset-library)