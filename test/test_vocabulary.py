from random import randint

from pydantic import confloat, conint

from tiro.model import Entity, Telemetry, Attribute, EntityList

temperature_type = confloat(ge=0, le=50)


class Server(Entity):
    # Telemetries
    CPUTemperature: Telemetry(temperature_type, "°C", )
    MemoryTemperature: Telemetry(temperature_type, "°C")
    FanSpeed: Telemetry(conint(ge=0, le=10000))

    # Attributes
    ModelName: Attribute(str)


class Rack(Entity):
    # Telemetries
    FrontTemperature: Telemetry(temperature_type, "°C")
    BackTemperature: Telemetry(temperature_type, "°C")

    # Entities
    Server: EntityList(Server, faking_number=lambda: randint(2, 20))


class Room(Entity):
    # Telemetries
    Temperature: Telemetry(temperature_type, "°C")

    # Attributes
    Site: Attribute(str)

    # Entities
    Rack: EntityList(Rack, faking_number=10)
    Server: EntityList(Server, faking_number=5)


yaml = """
- Site
- Rack:
    - BackTemperature
    - Server:
        - CPUTemperature
        - MemoryTemperature
- Server:
    - CPUTemperature
- Temperature
"""

scenario = Room()
scenario.Rack.FrontTemperature.use()
scenario.requires(yaml=yaml)

print(scenario.model(hide_data_points=False).schema_json(indent=2))
