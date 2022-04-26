# Tiro

The complete toolchain for DCWiz data interface development, data validation, data exchanging and mock data generation

## About

![Tiro Concepts](docs/Tiro%20concepts.svg)

The purpose of this project is to accelerate and standardize the development procedure of data interfacing for the DCWiz
platform. More specifically, it provides tools to

1. generate formal JSON schema to describe data points in a data center required by multiple use cases;
2. automatically generate mock data for the required data points;
3. validate and evaluate the quality of the data collected from other systems;
4. provide the plugins of Karez framework to collect data;
5. provide the data pump of Utinni toolkit for making use of the collected data or mock data.

## Concepts

* **Entity**: A device, equipment or virtual group in a data center. An entity can have several child entities.
* **Data Point**: A *telemetry* or *attribute* of the entity.
* **Scenario**: A scenario contains the following information:
  * The entity tree;
  * The data points defined in each entity;
* **Schema**: A [JSON schema](https://json-schema.org/) to describe the scenario.
* **Use Case**: A use case defines the required data points on different entites for a particular service or application that uses DCWiz platform.
* **Entity ID**: Each entity has a unique identifier.

### Example

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

A [schema](docs/schema.json) will be generated for formally describing the entity tree and the required data points. The schema can then be used to validate the collected data, to check if all the needed data points have been collected within a short period of time.

## Quickstart

### Defining a scenario and multiple use cases

To use tiro tools, first, we need to define a scenario ([example](demo/config/scenario.yaml)) file and several uses files ([exmaple](demo/config/use1.yaml)).

### Generating data schema and examples

```bash
tiro schema show config/scenario.yaml config/use1.yaml -o ../docs/schema.json
```

This command will generate the schema and save it to [this file](docs/schema.json). Or, without the `-o` option, it will print the generated schema to stdout.

Usually, the schema can be a little bit difficult for human to read. In such cases, the following command can generate an example that matches the schema.

```bash
tiro schema example config/scenario.yaml config/use1.yaml -o ../docs/example.json
```

The generated json example can be viewed [here](docs/example.json). Again, without the `-o` option, it will print the generated example to stdout.

### Mock data generater

The following command will setup a web server that generates mock data for each data point required by at least one use case.

```bash
tiro mock serve config/scenario.yaml config/use1.yaml -p 8000
```

Once the server has started, the documentation can be accessed on [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). Essentially, there will be an endpoint for each data point. For example, the data point with the path `Room.8f14567a-c582-11ec-852a-aa966665d395.Telemetry.Temperature` can be fetched from `GET http://127.0.0.1:8000/points/Room.8f14567a-c582-11ec-852a-aa966665d395.Telemetry.Temperature`. The list of all data point path can be retrieved from `GET http://127.0.0.1:8000/points/`.

With the server running, one can deploy a karez framwork to collect mock data points and test the application without intergating to real data center.

### Data validator

Sometimes, one may want to find out whether the data collection procedure can successfully retrieve all the data points it requires. This usually happens when the application and data collection procedure are developed by different teams. In this case, a validator server can be setup to validate the collected data.

```bash
tiro validate serve config/scenario.yaml config/use1.yaml -p 8001 -r 60
```

Again, once the server has started, the documentation can be accessed on [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs). The server will continuously receive data points, and validate the collected data every 60 seconds. Basically, it will assemble all the data points received within the minutes and combine them into a json like the [example](docs/example.json), and validate the json against the [schema](docs/schema.json). If the validation is passed, it should indicate that all the required data points has been collected. The interval can be adjust.

Alternatively, there also a Karez aggregator that can work as a validator, check [here](demo/config/karez_mock.yaml) for more details.

### Karez plugins

There several Karez plugins can be find in the project:

* `tiro.plugins.karez.ConnectorForMockServer`: a connector plugin to collect data from the mock server or any other server provides the same endpoints.
* `tiro.plugins.karez.TiroConverter`: a converter to format Tiro data. (To be detailed.)
* `tiro.plugins.karez.DispatcherForMockServer`: a connector to dispatch data collection tasks from the mocker server
* `tiro.plugins.karez.ValidationAggregator`: an aggregator works as a validator, it listens to all data point collection messages and validate the data periodically. The validation logs will be write to a log file.
* `tiro.plugins.karez.ArangoAggregator`: an aggregator to store tiro data points in the [ArangoDB](https://www.arangodb.com/) graph database. (Details to be discussed later.)

A example Karez configuration can be found [here](demo/config/karez_mock.yaml). Also, an complete stack docker compose example involving the full procedure of mock data generation, data collection and data validation can be found [here](demo/config/../tiro_mock.docker-compose.yml).

### Data collection protocol

To be complete.

### Use of collected data

To be complete.
