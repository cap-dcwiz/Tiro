# Quickstart

## Defining a scenario and multiple use cases

To use tiro tools, first, we need to define a scenario ([example](https://github.com/cap-dcwiz/Tiro/blob/main/demo/config/scenario.yaml)) file and several uses files ([exmaple](https://github.com/cap-dcwiz/Tiro/blob/main/demo/config/use1.yaml)).

## Generating data schema and examples

```bash
tiro schema show config/scenario.yaml config/use1.yaml -o schema.json
```

This command will generate the schema and save it to [this file](https://github.com/cap-dcwiz/Tiro/blob/main/demo/schema.json). Or, without the `-o` option, it will print the generated schema to stdout.

Usually, the schema can be a little bit difficult for human to read. In such cases, the following command can generate an example that matches the schema.

```bash
tiro schema example config/scenario.yaml config/use1.yaml -o example.json
```

The generated json example can be viewed [here](https://github.com/cap-dcwiz/Tiro/blob/main/demo/example.json). Again, without the `-o` option, it will print the generated example to stdout.

## Mock data generater

The following command will setup a web server that generates mock data for each data point required by at least one use case.

```bash
tiro mock serve config/scenario.yaml config/use1.yaml -p 8000
```

Once the server has started, the documentation can be accessed on [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). Essentially, there will be an endpoint for each data point. For example, the data point with the path `Room.8f14567a-c582-11ec-852a-aa966665d395.Telemetry.Temperature` can be fetched from `GET http://127.0.0.1:8000/points/Room.8f14567a-c582-11ec-852a-aa966665d395.Telemetry.Temperature`. The list of all data point path can be retrieved from `GET http://127.0.0.1:8000/points/`.

With the server running, one can deploy a karez framwork to collect mock data points and test the application without intergating to real data center.

## Data validator

Sometimes, one may want to find out whether the data collection procedure can successfully retrieve all the data points it requires. This usually happens when the application and data collection procedure are developed by different teams. In this case, a validator server can be setup to validate the collected data.

```bash
tiro validate serve config/scenario.yaml config/use1.yaml -p 8001 -r 60
```

Again, once the server has started, the documentation can be accessed on [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs). The server will continuously receive data points, and validate the collected data every 60 seconds. Basically, it will assemble all the data points received within the minutes and combine them into a json like the [example](https://github.com/cap-dcwiz/Tiro/blob/main/demo/example.json), and validate the json against the [schema](https://github.com/cap-dcwiz/Tiro/blob/main/demo/schema.json). If the validation is passed, it should indicate that all the required data points has been collected. The interval can be adjust.

Alternatively, there also a Karez aggregator that can work as a validator, check [here](https://github.com/cap-dcwiz/Tiro/blob/main/demo/config/karez_mock.yaml) for more details.

## Karez plugins

There several Karez plugins can be find in the project:

* `tiro.plugins.karez.ConnectorForMockServer`: a connector plugin to collect data from the mock server or any other server provides the same endpoints.
* `tiro.plugins.karez.TiroConverter`: a converter to format Tiro data. (To be detailed.)
* `tiro.plugins.karez.DispatcherForMockServer`: a connector to dispatch data collection tasks from the mocker server
* `tiro.plugins.karez.ValidationAggregator`: an aggregator works as a validator, it listens to all data point collection messages and validate the data periodically. The validation logs will be write to a log file.
* `tiro.plugins.karez.ArangoAggregator`: an aggregator to store tiro data points in the [ArangoDB](https://www.arangodb.com/) graph database. (Details to be discussed later.)

A example Karez configuration can be found [here](https://github.com/cap-dcwiz/Tiro/blob/main/demo/config/karez_mock.yaml). Also, an complete stack docker compose example involving the full procedure of mock data generation, data collection and data validation can be found [here](https://github.com/cap-dcwiz/Tiro/blob/main/demo/tiro_mock.docker-compose.yml).

## Data collection protocol

To be complete.

## Use of collected data

To be complete.
