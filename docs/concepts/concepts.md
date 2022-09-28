# Concepts

## Architecture

![Tiro Architecture](tiro%20concepts.svg)

## Definitions

`Entity`

:   A device, equipment or virtual group in a data center. An entity can have several child entities.

`Data Point`

:   A *telemetry* or *attribute* of the entity. 

`Scenario`

:   A scenario contains the following information: 1) the entity tree; 2) the data points defined in each entity.

`Schema`

:   A [JSON schema](https://json-schema.org/) to describe the scenario.

`Uses`

:   A use case defines the required data points on different entites for a particular service or application that uses DCWiz platform.
