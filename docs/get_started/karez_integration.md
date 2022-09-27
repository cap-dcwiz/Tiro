# Karez Integration

We have developed a data collection framework for DCWiz called [Karez](https://github.com/cap-dcwiz/Karez). Tiro provides deep integration with Karez. In this section, we will show how to use Tiro and Karaz together to build the complete data collection and processing workflow for a IoT system.


## Prerequisites

Karez should already be declared as a dependency of **Tiro**. Thus, you do not need to install Karez separately. 

However, before we start, we still need to set up [InfluxDB](https://www.influxdata.com/products/influxdb-overview/) and [ArangoDB](https://www.arangodb.com/). Tiro uses InfluxDB to store the collected telemetries for assets and uses ArangoDB to store the attributes and relationships of the assets.

To simplify the setup process, we will use [Docker Compose](https://docs.docker.com/compose/) to start the two databases and the Karez components. Please refer to the [Docker documentation](https://docs.docker.com/compose/install/) to install Docker Compose.

Let's create a file named `docker-compose.yml` with the following content:

=== "docker-compose.yml"

    ```yaml
    version: '3.9'

    services:
      influxdb:
        image: influxdb:alpine
        restart: always
        ports:
          - 8086:8086
        environment:
          DOCKER_INFLUXDB_INIT_MODE: setup
          DOCKER_INFLUXDB_INIT_USERNAME: tiro
          DOCKER_INFLUXDB_INIT_PASSWORD: tiro-password
          DOCKER_INFLUXDB_INIT_ORG: tiro
          DOCKER_INFLUXDB_INIT_BUCKET: tiro
          DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: tiro-token

      arangodb:
        image: arangodb/arangodb:3.8.6
        platform: linux/amd64
        restart: always
        ports:
          - 8529:8529
        environment:
          ARANGO_ROOT_PASSWORD: tiro-password
        command: arangod --server.endpoint tcp://0.0.0.0:8529

      nats-server:
        image: nats
        restart: always
        ports:
          - 4222:4222
          - 8222:8222
    ```



## Overview

In the following subsections, we will set up following components:

1. A mock server to generate mock data;
2. A set of Karez roles to collect the mock data;
3. A set of Karez roles to transform the mock data;
4. A validator to validate the collected data;
5. A set of Karez roles to persist the collected data in databases.

The complete source code of the example can be found under the `example/karez` directory of the Tiro repository.

## Directory Setup

Let's create a directory named `karez` and follow the following steps to set up the directory structure and initial files:

1. Create a sub-directory name `scenario` to store the scenario files. After that, copy the `scenario.yaml`, `use-srv1.yaml` and `use-srv2.yaml` into this directory. 
2. Create subdirectory named `karez` and create four subdirectories named `dispatcher`, `connector`, `converter` and `aggregator` in the `karez` directory. We will use these directories to arrange Karez roles.
3. Create a subdirectory named `config` to store various configuration files. 
4. Create a file named `karez.yml` in `config` directory. This file will be used to configure the Karez components.
5. Copy the just created `docker-compose.yml` into the `karez` directory and run the following command to start the databases and Karez components:

```console
$ docker-compose up -d --build
```

## Mock Server

Run the following command to create a mock server:

```console
$ tiro mock serve scenario/scenario.yaml scenario/use-srv1.yaml scenario/use-srv2.yaml
```

Alternative, you can also add the following section to the `docker-compose.yml` file 

=== "docker-compose.yml"

    ```yaml
      mock-server:
        image: ghcr.io/cap-dcwiz/tiro
        restart: always
        volumes:
          - ./scenario:/tiro/scenario
          - ./test-assets.py:/tiro/test-assets.p
        command: tiro mock serve scenario/scenario.yaml scenario/use-srv1.yaml scenario/use-srv2.yaml -h 0.0.0.0
    ```

After that, you need to run `docker-compose up -d` to start the mock server.

## Karez Collector

Here, we will config Karez to collect data point from the mock server. Tiro provides a _connector_ plugin `ConnectorForMockServer` and a _dispatcher_ plugin `DispatcherForMockServer` to collect data from the mock server. We will use these two plugins to collect data from the mock server.

First, let's add a `tiro_mock.py` file to the `karez/connector` directory with the following content:

=== "karez/connector/tiro_mock.py" 

    ```py
    from tiro.plugins.karez import ConnectorForMockServer as Connector
    ```

And add another `tiro_mock.py` file to the `karez/dispatcher` directory with the following content:

=== "karez/dispatcher/tiro_mock.py" 

    ```py
    from tiro.plugins.karez import DispatcherForMockServer as Dispatcher
    ```

After that, let's add the following section to the `karez.yaml` file:

=== "config/karez.yaml"

    ```yaml
    dispatchers:
      - type: tiro_mock
        connector: tiro_mock
        by: path
        batch_size: 10
        interval: 10
        mode: burst
        base_url: http://localhost:8000

    connectors:
      - type: tiro_mock
        base_url: http://localhost:8000
        by: path
    ```

Run the following command to varify the configuration:

```console
$ karez test -c config/karez.yaml -p karez/ -d tiro_mock -n tiro_mock
{
    'path': 'DataHall.data_hall_0.CRAC.crac_0.Telemetry.ReturnTemperature',
    'result': {'value': 38.15, 'timestamp': '2022-09-27T10:32:38.364195'},
    '_karez': {'category': 'telemetry'}
}
```

If you see similar output, it means the configuration is correct. Otherwise, you may use the `-d` or `-n` option to varify the configuration of a specific dispatcher or connector.


## Karez Validator

Tiro provides an _aggregator_ plugin `ValidationAggregator` to validate the collected data. Now let's validate our collected data using this plugin. 

First, let's add a `tiro_validate.py` file to the `karez/aggregator` directory with the following content:

=== "karez/aggregator/tiro_validate.py"

    ```py
    from tiro.plugins.karez import ValidationAggregator as Aggregator
    ```

After that, let's add the following section to the `karez.yaml` file:

=== "config/karez.yaml"

    ```yaml
    converters:
      - name: update_category_for_validator
        type: filter_and_update_meta
        key: category
        rename:
          telemetry: validation_data
          attribute: validation_data

    aggregators:
      - type: tiro_validate
        category: validation_data
        scenario: scenario/scenario.yaml
        uses: "scenario/use-srv1.yaml,scenario/use-srv2.yaml"
        retention: 10
        log_file: validation.log
    ```

Also, add the highlighted lines to the `connectors - tiro_mock` section:

=== "config/karez.yaml"

    ```yaml hl_lines="5 6"
    connectors:
      - type: tiro_mock
        base_url: http://localhost:8000
        by: path
        converters:
          - update_category_for_validator
    ```

With the above configuration, we have set up a validation aggregator listening on the `validation_data` category. The validation aggregator will validate the collected data against the scenario files `scenario/scenario.yaml`, `scenario/use-srv1.yaml` and `scenario/use-srv2.yaml`. The validation result will be stored in the `validation.log` file as well as printed to the console. The validation will be executed every 10 seconds, using the last 10 seconds of data.

Now, we can deploy the Karez workflow by running the following command:

```console
$ karez deploy -c config/karez.yaml -p karez/
```

Wait for around 10 seconds, and you will see the validation result printed to the console:

```console
[KAREZ] Configurations: ['config/karez.yaml'].
[KAREZ] NATS address: nats://localhost:4222.
[KAREZ] Launched 1 Converters.
[KAREZ] Launched 1 Connectors.
[KAREZ] Launched 1 Dispatchers.
[KAREZ] Launched 1 Aggregators.
 Collection size: 11
{
  "start": "2022-09-27T11:39:24.255426",
  "end": "2022-09-27T11:39:34.255426",
  "valid": true,
  "exception": null
}
```

The above result means the collected data is valid. If the collected data is invalid, the `valid` field will be set to `false` and the `exception` field will contain the error message. Meanwhile, the validation will be written to the `validation.log` file as well.

!!! note

    Because currently we are using the mocking service, which always produce corrent data, the validation result will always be `true`. In a real environment, we can simply replace the dispatcher and connector with the real service, and the validation will be performed on the real data. This provides a way to validate the real data collection process.

## Data Persistence

Now, let's add more Karez roles to persist the collected data. Tiro stores the data in both InfluxDB and ArangoDB, where the former is used to store the time series data and the latter is used to store static attributes and relationships.

### Preprocessing

Before storing the data to databases, some preprocessing is needed to convert data format and add some metadata. Tiro provides a _converter_ plugin `TiroPreprocessConverter` to do these. First, let's add a `tiro_preprocess.py` file to the `karez/converter` directory with the following content:

=== "kalrez/converter/tiro_preprocess.py"

    ```py
    from tiro.plugins.karez import TiroPreprocessConverter as Converter
    ```

Then, add the following content in the `converters` section of the `karez.yaml` file:

=== "config/karez.yaml"

    ```yaml
      - type: tiro_preprocess
        tz_infos:
          SGT: Aisa/Singapore
        next:
          - influx_line_protocol
          - update_category_for_arangodb
    ```

Also, we need to add the convertor into the processing pipeline by adding the following highlighted line to the `connectors - tiro_mock` section:

=== "config/karez.yaml"

    ```yaml hl_lines="7"
    connectors:
      - type: tiro_mock
        base_url: http://localhost:8000
        by: path
        converter:
          - update_category_for_validator
          - tiro_preprocess
    ```

We can run the following command to test the configuration:

```console
$ karez test -c config/karez.yaml -p karez/ -d tiro_mock -n tiro_mock -v tiro_preprocess
{
    'path': 'DataHall.CRAC.ReturnTemperature',
    'asset_path': 'DataHall.data_hall_0.CRAC.crac_0',
    'DataHall': 'data_hall_0',
    'CRAC': 'crac_0',
    'type': 'Telemetry',
    'field': 'ReturnTemperature',
    'value': 23.84,
    'timestamp': 1664251882.666721
}
```

### InfluxDB

We will use [Telegraf](https://www.influxdata.com/time-series-platform/telegraf/) to send the data to InfluxDB. First, let add the following service in the `docker-compose.yml` file:

=== "docker-compose.yml"

    ```yaml
      telegraf:
        image: telegraf
        restart: always
        volumes:
          - ./config/telegraf.conf:/etc/telegraf/telegraf.conf
    ```

Then, let's add a `telegraf.conf` file with the following content in the `config` directory:

=== "config/telegraf.conf"

    ```toml
    [[outputs.influxdb_v2]]
     urls = ["http://localhost:8086"]
     token = "tiro-token"
     organization = "tiro"
     bucket = "tiro"

    [[inputs.nats_consumer]]
      servers = ["nats://localhost:4222"]
      subjects = ["karez.telemetry.>"]
      queue_group = "karez_telegraf"
      data_format = "influx"
    ```

The above configuration tells Telegraf to listen on the `karez.telemetry.*` subject and send the data to InfluxDB. After adding/modifying the configuration, you need to run `docker-compose up -d` to update the services.

Now, let's add the following converter in the `converters` sections of `karez.yaml`:

=== "config/karez.yaml"

    ```yaml
      - type: influx_line_protocol
        measurement: tiro_telemetry
        field_name: field
        field_value: value
    ```

This converter translates the preprocessed data into the InfluxDB line protocol format. The `measurement` field specifies the measurement name, and the `field_name` and `field_value` fields specify the columns that will be used as field and value in the line protocol.


### ArangoDB

Tiro also provides an _aggregator_ plugin `ArangoAggregator` to store the data to ArangoDB. First, let's add a `arango_db.py` file to the `karez/aggregator` directory with the following content:

=== "karez/aggregator/arango_db.py"

    ```py
    from tiro.plugins.karez import ArangoAggregator as Aggregator
    ```

Then, to avoid confusing the data with those sending to InfluxDB and validator, we added another converter to mark the data as `graph_data`.

=== "config/karez.yaml"

    ```yaml
      - name: update_category_for_arangodb
        type: filter_and_update_meta
        key: category
        rename:
          telemetry: graph_data
          attribute: graph_data
    ```

After that, we can add the following aggregator in the `aggregators` section of `karez.yaml`:

=== "config/karez.yaml"

    ```yaml
      - type: arango_db
        category: graph_data
        scenario: scenario/scenario.yaml
        uses: "scenario/use-srv1.yaml,scenario/use-srv2.yaml"
        db_name: tiro
        graph_name: scenario
        hosts: http://localhost:8529
        auth:
          password: tiro-password
    ```

## Deployment 

Now, we can re-deploy the Karez service to start the data persistence process.

```console
$ karez deploy -c config/karez.yaml -p karez/
[KAREZ] Configurations: ['config/karez.yaml'].
[KAREZ] NATS address: nats://localhost:4222.
[KAREZ] Launched 4 Converters.
[KAREZ] Launched 1 Connectors.
[KAREZ] Launched 1 Dispatchers.
[KAREZ] Launched 2 Aggregators.
```

!!! note

    We can also include the karez workflow and mock service in `docker-compose.yml` to deploy them together. In that case, remember to change different hostnames corresponding to the services.

Now, one should be able to access [http://localhost:8086](http://localhost:8086) to see the data in InfluxDB or access [http://localhost:8529](http://localhost:8529) to see the data in ArangoDB.

In next section, we will show how to use [Utinni]("https://github.com/cap-dcwiz/Utinni") to access the data easily.