# Basic Tools

The basic features of Tiro are provided by the `tiro` command line tool. In last section, we have seen how to use `tiro schema` command to generate an example of data point collection that conforms to the scenario definition and use case requirements. In this section, we will introduce the other basic tools provided by `tiro` command.

## Schema and Example

### Generate Formal Schema

One common task in DCWiz data interface development is to find the list of data point info that are required by multiple use cases. This information should include not only the list of data point names, but also the data type, unit, hierarchy structure, etc. 

Tiro provides the tool to gather data requirements from different services and applications and generate a formal [JSON schema](https://json-schema.org/) from the scenario. The schema can be used to describe the data requirement, to validate the data actually collected, or to generate mock data.

To generate the schema, run the following command:

```console
$ tiro schema show scenario.yaml use-srv1.yaml use-srv2.yaml -o schema.json
```

Here, we demonstrate the schema generation for two use cases. The generated `schema.json` file should be like: 

=== "schema.json"

    ```json
    {
      "title": "Scenario",
      "type": "object",
      "properties": {
        "DataHall": {
          "title": "Datahall",
          "type": "object",
          "additionalProperties": {
            "$ref": "#/definitions/Scenario_DataHall"
          }
        }
      },
      "required": [
        "DataHall"
      ],
      "definitions": {
        "Scenario_DataHall_CRAC_ActivePower": {
          "title": "Scenario_DataHall_CRAC_ActivePower",
          "description": "Base Pydantic Model to representing a data point",
          "type": "object",
          "properties": {
            "value": {
              "minimum": 0,
              "maximum": 1000,
              "type": "number"
            },
            "timestamp": {
              "type": "string",
              "format": "date-time"
            }
          },
          "required": [
            "value",
            "timestamp"
          ],
          "unit": null
        },
        "Scenario_DataHall_CRAC_SupplyTemperature": {
          "title": "Scenario_DataHall_CRAC_SupplyTemperature",
          "description": "Base Pydantic Model to representing a data point",
          "type": "object",
          "properties": {
            "value": {
              "minimum": 0,
              "maximum": 50,
              "type": "number"
            },
            "timestamp": {
              "type": "string",
              "format": "date-time"
            }
          },
          "required": [
            "value",
            "timestamp"
          ],
          "unit": null
        },
        "Scenario_DataHall_CRAC_ReturnTemperature": {
          "title": "Scenario_DataHall_CRAC_ReturnTemperature",
          "description": "Base Pydantic Model to representing a data point",
          "type": "object",
          "properties": {
            "value": {
              "minimum": 0,
              "maximum": 50,
              "type": "number"
            },
            "timestamp": {
              "type": "string",
              "format": "date-time"
            }
          },
          "required": [
            "value",
            "timestamp"
          ],
          "unit": null
        },
        "Scenario_DataHall_CRAC_Telemetry": {
          "title": "Scenario_DataHall_CRAC_Telemetry",
          "type": "object",
          "properties": {
            "ActivePower": {
              "$ref": "#/definitions/Scenario_DataHall_CRAC_ActivePower"
            },
            "SupplyTemperature": {
              "$ref": "#/definitions/Scenario_DataHall_CRAC_SupplyTemperature"
            },
            "ReturnTemperature": {
              "$ref": "#/definitions/Scenario_DataHall_CRAC_ReturnTemperature"
            }
          },
          "required": [
            "ActivePower",
            "SupplyTemperature",
            "ReturnTemperature"
          ]
        },
        "Scenario_DataHall_CRAC": {
          "title": "Scenario_DataHall_CRAC",
          "type": "object",
          "properties": {
            "Telemetry": {
              "$ref": "#/definitions/Scenario_DataHall_CRAC_Telemetry"
            }
          },
          "required": [
            "Telemetry"
          ]
        },
        "Scenario_DataHall_Rack_Server_FlowRate": {
          "title": "Scenario_DataHall_Rack_Server_FlowRate",
          "description": "Base Pydantic Model to representing a data point",
          "type": "object",
          "properties": {
            "value": {
              "minimum": 0,
              "maximum": 1000,
              "type": "number"
            },
            "timestamp": {
              "type": "string",
              "format": "date-time"
            }
          },
          "required": [
            "value",
            "timestamp"
          ],
          "unit": null
        },
        "Scenario_DataHall_Rack_Server_Telemetry": {
          "title": "Scenario_DataHall_Rack_Server_Telemetry",
          "type": "object",
          "properties": {
            "FlowRate": {
              "$ref": "#/definitions/Scenario_DataHall_Rack_Server_FlowRate"
            }
          },
          "required": [
            "FlowRate"
          ]
        },
        "Scenario_DataHall_Rack_Server": {
          "title": "Scenario_DataHall_Rack_Server",
          "type": "object",
          "properties": {
            "Telemetry": {
              "$ref": "#/definitions/Scenario_DataHall_Rack_Server_Telemetry"
            }
          },
          "required": [
            "Telemetry"
          ]
        },
        "Scenario_DataHall_Rack_ActivePower": {
          "title": "Scenario_DataHall_Rack_ActivePower",
          "description": "Base Pydantic Model to representing a data point",
          "type": "object",
          "properties": {
            "value": {
              "minimum": 0,
              "maximum": 1000,
              "type": "number"
            },
            "timestamp": {
              "type": "string",
              "format": "date-time"
            }
          },
          "required": [
            "value",
            "timestamp"
          ],
          "unit": null
        },
        "Scenario_DataHall_Rack_Telemetry": {
          "title": "Scenario_DataHall_Rack_Telemetry",
          "type": "object",
          "properties": {
            "ActivePower": {
              "$ref": "#/definitions/Scenario_DataHall_Rack_ActivePower"
            }
          },
          "required": [
            "ActivePower"
          ]
        },
        "Scenario_DataHall_Rack": {
          "title": "Scenario_DataHall_Rack",
          "type": "object",
          "properties": {
            "Server": {
              "title": "Server",
              "type": "object",
              "additionalProperties": {
                "$ref": "#/definitions/Scenario_DataHall_Rack_Server"
              }
            },
            "Telemetry": {
              "$ref": "#/definitions/Scenario_DataHall_Rack_Telemetry"
            }
          },
          "required": [
            "Server",
            "Telemetry"
          ]
        },
        "Scenario_DataHall": {
          "title": "Scenario_DataHall",
          "type": "object",
          "properties": {
            "CRAC": {
              "title": "Crac",
              "type": "object",
              "additionalProperties": {
                "$ref": "#/definitions/Scenario_DataHall_CRAC"
              }
            },
            "Rack": {
              "title": "Rack",
              "type": "object",
              "additionalProperties": {
                "$ref": "#/definitions/Scenario_DataHall_Rack"
              }
            }
          },
          "required": [
            "CRAC",
            "Rack"
          ]
        }
      }
    }
    ```

Then, this file can be distributed to the client or system integrator to as a reference for required information. Or it can be shared among different teams using as a reference for the data model. This is a great way to share the data model with other systems and to ensure that the data model is consistent across the entire system.

### Generate Example

The JSON schema is good for precise data model definition. However, it is not easy to read and understand. Therefore, one can also use the following command to generate an example JSON file for better understanding of the data model.

```console
$ tiro schema example -c scenario.yaml use-srv1.yaml use-srv2.yaml -o example.json
```

### Use Schema to Validate Data

The JSON schema can be used to validate the data model. For example, here we let's generate an example file that considering only srv2's requirements.

```console
$ tiro schema example scenario.yaml use-srv2.yaml -o data_srv2.json
```

Then, we can validate the data model using the JSON schema which considers both srv1 and srv2's requirements.

```console
$ tiro validate test scenario.yaml use-srv1.yaml use-srv2.yaml data_srv2.json
Validation failed!
ValidationError(
    model='Scenario',
    errors=[
        {
            'loc': ('DataHall', 'data_hall_0', 'CRAC', 'crac_0', 'Telemetry', 'ActivePower'),
            'msg': 'field required',
            'type': 'value_error.missing'
        },
        {
            'loc': ('DataHall', 'data_hall_0', 'Rack', 'rack_0', 'Telemetry'),
            'msg': 'field required',
            'type': 'value_error.missing'
        },
        {
            'loc': ('DataHall', 'data_hall_0', 'Rack', 'rack_1', 'Telemetry'),
            'msg': 'field required',
            'type': 'value_error.missing'
        }
    ]
)
```

As we can see, the validation failed because the data points required by srv1 are missing. The tool can then explicitly tell us which data points are missing.

!!! tip

    However, in most cases, the system integrator to provide such a json file for validate. It provides more convient tool to directly integrate the validation process into the data collection process. Please refer to [Data Collection](/docs/data-collection) for more details.

## Mocking Data

A big challenger in DCWiz projects is the lack of real data. Usually, the system can only be connected to the real environment after the system is deployed. However, the system needs to be tested and validated before deployment. In this case, mock data is required to simulate the real data. Tiro provides a tool to generate mock data that conforms to the scenario definition and data point requirements.

### Service

Running the mocking service is as simple as running the following command:

```console
$ tiro mock serve scenario.yaml use-srv1.yaml use-srv2.yaml
```

This command will start a server that listens on port 8000. The documentation of the server can be found at [http://localhost:8000/docs](http://localhost:8000/docs). 

### Endpoints

Main endpoints of the mocking service include:

* GET `/sample`: generate a sample snapshot of the scenario

```console
$ curl -X 'GET' \
  'http://127.0.0.1:8001/sample?change_attrs=false' \
  -H 'accept: application/json'
{
  "DataHall": {
    "data_hall_0": {
      "CRAC": {
        "crac_0": {
          "Telemetry": {
            "ActivePower": {
              "value": 656.65,
              "timestamp": "2022-09-26T23:45:50.938966"
            },
            "SupplyTemperature": {
              "value": 13.95,
              "timestamp": "2022-09-26T23:45:50.895489"
            },
            "ReturnTemperature": {
              "value": 6.38,
              "timestamp": "2022-09-26T23:45:50.508399"
            }
          }
        }
      },
      "Rack": {
        "rack_0": {
          "Server": {
            "server_0": {
              "Telemetry": {
                "FlowRate": {
                  "value": 995.96,
                  "timestamp": "2022-09-26T23:45:50.491637"
                }
              }
            },
            "server_1": {
              "Telemetry": {
                "FlowRate": {
                  "value": 933.36,
                  "timestamp": "2022-09-26T23:45:50.984197"
                }
              }
            }
          },
          "Telemetry": {
            "ActivePower": {
              "value": 460.68,
              "timestamp": "2022-09-26T23:45:50.117701"
            }
          }
        },
        "rack_1": {
          "Server": {
            "server_2": {
              "Telemetry": {
                "FlowRate": {
                  "value": 841.52,
                  "timestamp": "2022-09-26T23:45:50.017445"
                }
              }
            },
            "server_3": {
              "Telemetry": {
                "FlowRate": {
                  "value": 115.27,
                  "timestamp": "2022-09-26T23:45:50.686074"
                }
              }
            },
            "server_4": {
              "Telemetry": {
                "FlowRate": {
                  "value": 330.98,
                  "timestamp": "2022-09-26T23:45:50.208213"
                }
              }
            }
          },
          "Telemetry": {
            "ActivePower": {
              "value": 827.3,
              "timestamp": "2022-09-26T23:45:50.432735"
            }
          }
        }
      }
    }
  }
}
```

* GET `/points`: list all data points in the scenario

```console
$curl -X 'GET' \
  'http://127.0.0.1:8001/points/' \
  -H 'accept: application/json'
[
  "DataHall.data_hall_0.CRAC.crac_0.Telemetry.ActivePower",
  "DataHall.data_hall_0.CRAC.crac_0.Telemetry.SupplyTemperature",
  "DataHall.data_hall_0.CRAC.crac_0.Telemetry.ReturnTemperature",
  "DataHall.data_hall_0.Rack.rack_0.Telemetry.ActivePower",
  "DataHall.data_hall_0.Rack.rack_0.Server.server_0.Telemetry.FlowRate",
  "DataHall.data_hall_0.Rack.rack_0.Server.server_1.Telemetry.FlowRate",
  "DataHall.data_hall_0.Rack.rack_1.Telemetry.ActivePower",
  "DataHall.data_hall_0.Rack.rack_1.Server.server_2.Telemetry.FlowRate",
  "DataHall.data_hall_0.Rack.rack_1.Server.server_3.Telemetry.FlowRate",
  "DataHall.data_hall_0.Rack.rack_1.Server.server_4.Telemetry.FlowRate"
]
```

* GET `/points/{point}`: get current value of a data point

```console
$ curl -X 'GET' \
  'http://127.0.0.1:8001/points/DataHall.data_hall_0.Rack.rack_0.Telemetry.ActivePower' \
  -H 'accept: application/json'
{
  "value": 378.61,
  "timestamp": "2022-09-26T23:48:55.812522"
}
```

The mocking service can then be used as a generator of mock data for system development and testing. 

## Validation

In a large system, it would be common that the data collector and the data consumer are belongs to different system modules that developed by different teams. In this case, the data consumer may not be able to validate the completeness and correctness of the data collected from the data collector. To solve this problem, Tiro provides a data validation tool.

In [previous section](#use-schema-to-validate-data), we have shown how to use the schema to validate a data collection. However, in real environment, the data points may not be collected in a batch and with a formal format. Instead, the discrete data points may be collected from different sources in a discrete manner. In this case, the previous validation method may not be applicable. Therefore, in this section we introduce a validation tool that can discretely receive data points and validate them against the schema.

### Service

A validation service can be setup by running the following command:

```console
$ tiro validate serve scenario.yaml use-srv1.yaml use-srv2.yaml -p 8001 -r 60
```

The service works as an HTTP server that listens on port 8001. The documentation of the server can be found at [http://localhost:8001/docs](http://localhost:8001/docs). 

Basically, the data collector needs to send data points to the service via the `/points/{path}` endpoint. And the service will periodically gather the data collected and validate them against the scenario definition. The validation result can be retrieved via the `/result` endpoint. By running the above command, the service will validate the data collected every 60 seconds.

Now, let's try to validate the data collected from the mocking service. First, we need to start the mocking service (in another terminal):

```console
$ tiro mock serve scenario.yaml use-srv1.yaml use-srv2.yaml -p 8002
```

Then, we need to forward the data points from the mocking service to the validation service. There is a built-in tool can do this. Run the following command in another terminal:

```console
$ tiro mock push -d 127.0.0.1:8001 -r 127.0.0.1:8002
Forwarding DataHall.data_hall_0.CRAC.crac_0.Telemetry.ActivePower
Forwarding DataHall.data_hall_0.CRAC.crac_0.Telemetry.ReturnTemperature
Forwarding DataHall.data_hall_0.CRAC.crac_0.Telemetry.SupplyTemperature
Forwarding DataHall.data_hall_0.Rack.rack_0.Telemetry.ActivePower
Forwarding DataHall.data_hall_0.Rack.rack_0.Server.server_0.Telemetry.FlowRate
Forwarding DataHall.data_hall_0.Rack.rack_0.Server.server_1.Telemetry.FlowRate
Forwarding DataHall.data_hall_0.Rack.rack_0.Server.server_2.Telemetry.FlowRate
Forwarding DataHall.data_hall_0.Rack.rack_0.Server.server_3.Telemetry.FlowRate
Forwarding DataHall.data_hall_0.Rack.rack_0.Server.server_4.Telemetry.FlowRate
Forwarding DataHall.data_hall_0.Rack.rack_1.Telemetry.ActivePower
Forwarding DataHall.data_hall_0.Rack.rack_1.Server.server_5.Telemetry.FlowRate
Forwarding DataHall.data_hall_0.Rack.rack_1.Server.server_6.Telemetry.FlowRate
Forwarding DataHall.data_hall_0.Rack.rack_1.Server.server_7.Telemetry.FlowRate
```

We should see some messages like above showing that the data points are being forwarded. 

### Results

Now, we can check the validation result by visiting [http://localhost:8001/result](http://localhost:8001/result).

```console
$ curl -X 'GET' \
          'http://127.0.0.1:8001/results' \
          -H 'accept: text/plain'
Validation Period: 2022-09-27 00:33:19.492201 -- 2022-09-27 00:34:10.997081
Successful!

Validation Period: 2022-09-27 00:32:19.259650 -- 2022-09-27 00:33:19.259650
Successful!

Validation Period: 2022-09-27 00:24:34.889349 -- 2022-09-27 00:25:34.889349
Failed!
1 validation error for Scenario
DataHall
  field required (type=value_error.missing)⏎
```

Depending on the timing, you may see different results. The validation result is a list of validation results. Each validation result contains the start and end time of the validation period, and the validation result itself. The validation result can be either `Successful` or `Failed`. If the validation result is `Failed`, the validation result will also contain the validation errors, e.g. missing data points, data points with invalid value, etc.