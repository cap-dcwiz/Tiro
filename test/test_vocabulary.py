from pprint import pprint
from random import randint

from pydantic import confloat, conint

from tiro.mock import MockedEntity
from tiro.vocabulary import Entity, Telemetry, Attribute, EntityList

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
    Servers: EntityList(Server, faking_number=lambda: randint(2, 20))


class Room(Entity):
    # Telemetries
    Temperature: Telemetry(temperature_type, "°C")

    # Attributes
    Site: Attribute(str)

    # Entities
    Racks: EntityList(Rack, faking_number=10)
    Servers: EntityList(Server, faking_number=5)


scenario = Room()
scenario.Racks.FrontTemperature.use()
scenario.requires(
    "Racks.BackTemperature",
    "Racks.Servers.CPUTemperature",
    "Racks.Servers.MemoryTemperature",
    "Servers.CPUTemperature",
    "Temperature"
)

# print(scenario.model(hide_data_points=False).schema_json(indent=2))
#
print(scenario.fake(include_data_points=True).json(indent=2))
#
# print(scenario.children["Racks"].mock_data_points())
