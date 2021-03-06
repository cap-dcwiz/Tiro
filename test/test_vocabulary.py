from pydantic import confloat, conint
from rich import print_json

from tiro.core import Scenario
from tiro.core.model import Entity, Telemetry, Attribute, EntityList

temperature_type = confloat(ge=0, le=50)


class Server(Entity):
    # Telemetries
    CPUTemperature: Telemetry(temperature_type, "°C", ) = 10
    MemoryTemperature: Telemetry(temperature_type, "°C")
    FanSpeed: Telemetry(conint(ge=0, le=10000))

    # Attributes
    ModelName: Attribute(str)


class Rack(Entity):
    # Telemetries
    FrontTemperature: Telemetry(temperature_type, "°C")
    BackTemperature: Telemetry(temperature_type, "°C")

    # Entities
    Server: EntityList(Server, faking_number=lambda: 10)


class Room(Entity):
    # Telemetries
    Temperature: Telemetry(temperature_type, "°C")

    # Attributes
    Site: Attribute(str)

    # Entities
    Rack: EntityList(Rack, faking_number=10)
    Server: EntityList(Server, faking_number=5)


yaml = """
- Room:
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

scenario = Scenario(Room)
scenario.Room.Rack.FrontTemperature.use()
scenario.requires(yaml=yaml)

print_json(scenario.model(hide_dp_values=True).schema_json())

print(scenario.all_required_paths())