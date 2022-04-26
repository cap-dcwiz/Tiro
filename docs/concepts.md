# Concepts

* **Entity**: A device, equipment or virtual group in a data center. An entity can have several child entities.
* **Data Point**: A *telemetry* or *attribute* of the entity.
* **Scenario**: A scenario contains the following information:
  * The entity tree;
  * The data points defined in each entity;
* **Schema**: A [JSON schema](https://json-schema.org/) to describe the scenario.
* **Use Case**: A use case defines the required data points on different entites for a particular service or application that uses DCWiz platform.
* **Entity ID**: Each entity has a unique identifier.

## Example

Let's consider a simple data center which contains several rooms (data halls). There are a lot of racks and servers in a room, and the server can be installed on a rack or not. In other words, the racks are child entities of the room, and the servers can be child entities of either racks or rooms.

The entity tree (scenario) can be presented as follows:

```yaml
$asset_library_path: .
$asset_library_name: assets

Room:
    $type: data_hall.Room
    $number: 2
    Rack:
        $type: data_hall.Rack
        $number: 10
        Server:
            $type: data_hall.Server
            $number: 2-20
    Server:
        $type: data_hall.Server
        $number: 5
```

Several available data points are predefined in the asset library for each entity type. For example, a room can have a name, a room temperature, a rack can have front temperature and back temperature, and a server can have CPU temperature, memory temperature amd Fan speed.

After that, a service or application can declare all the data points it wants:

```yaml
- Room:
    - Rack:
        - BackTemperature
        - Server:
            - CPUTemperature
    - Server:
        - CPUTemperature
    - Temperature
```

In the above example, the application declares that it needs the room's temperature, the rack's back temperature, and the server's CPU temperature. There can be different uses files for different applications or services. The tiro tools can assemble all the requires when generating schema or mock data.

A [schema](https://github.com/cap-dcwiz/Tiro/blob/main/demo/schema.json) will be generated for formally describing the entity tree and the required data points. The schema can then be used to validate the collected data, to check if all the needed data points have been collected within a short period of time.
