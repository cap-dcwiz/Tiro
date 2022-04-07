from pydantic import confloat, conint

from tiro.vocabulary import Entity, Telemetry, Attribute

temperature_type = confloat(ge=0, le=50)


class Server(Entity):
    CPUTemperature: Telemetry(temperature_type, "°C")
    MemoryTemperature: Telemetry(temperature_type, "°C")
    FanSpeed: Telemetry(conint(ge=0, le=10000))
    ModelName: Attribute(str)


class Rack(Entity):
    FrontTemperature: Telemetry(temperature_type, "°C")
    BackTemperature: Telemetry(temperature_type, "°C")


class Room(Entity):
    Temperature: Telemetry(temperature_type, "°C")
    Site: Attribute(str)


scenario = \
    Room(
        Rack(
            Server,
        ),
        Server,
    )

scenario.use("Temperature")
scenario.Rack.use("FrontTemperature")
scenario.Server.use("CPUTemperature")
scenario.Rack.Server.use("CPUTemperature")

print(scenario.model(hide_data_points=True).schema_json(indent=2))

# print(scenario.fake(include_data_points=False).json(indent=2))
