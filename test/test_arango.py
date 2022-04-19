from random import randint

from arango import ArangoClient
from faker import Faker
from pydantic import confloat, conint
from rich import print

from tiro.graphdb import ArangoAgent
from tiro.mock import Mocker
from tiro.model import Entity, Telemetry, Attribute, EntityList

temperature_type = confloat(ge=0, le=50)
faker = Faker()


def temperature_faker():
    return faker.pyfloat(right_digits=2, min_value=10, max_value=30)


class Server(Entity):
    # Telemetries
    CPUTemperature: Telemetry(temperature_type, "°C", faker=temperature_faker)
    MemoryTemperature: Telemetry(temperature_type, "°C", faker=temperature_faker)
    FanSpeed: Telemetry(conint(ge=0, le=10000), faker=lambda: faker.pyint(0, 10000))

    # Attributes
    ModelName: Attribute(str)


class Rack(Entity):
    # Telemetries
    FrontTemperature: Telemetry(temperature_type, "°C", faker=temperature_faker)
    BackTemperature: Telemetry(temperature_type, "°C", faker=temperature_faker)

    # Entities
    Server: EntityList(Server, faking_number=lambda: randint(2, 20))


class Room(Entity):
    # Telemetries
    Temperature: Telemetry(temperature_type, "°C", faker=temperature_faker)

    # Attributes
    Site: Attribute(str, faker=faker.company)

    # Entities
    Rack: EntityList(Rack, faking_number=10)
    Server: EntityList(Server, faking_number=5)


scenario = Room()
scenario.Rack.FrontTemperature.use()
scenario.Server.MemoryTemperature.use()
scenario.requires(
    "Site",
    "Rack.BackTemperature",
    "Rack.Server.CPUTemperature",
    "Rack.Server.MemoryTemperature",
    "Server.CPUTemperature",
    "Temperature"
)

mocker = Mocker(scenario)

gdb_client = ArangoAgent(scenario, "tiro_test", "scenario",
                         ArangoClient(hosts="http://localhost:8529"))

# gdb_client.create_graph(clear_existing=True, clear_database=True)
# for item in scenario.decompose_data("", mocker.dict()):
#     gdb_client.update(item)

# data = gdb_client.capture_status()
# print(scenario.model().parse_obj(data).json(indent=2))

data = gdb_client.capture_status(pattern=".*Server%(CPU|Memory)Temperature")
print(data)
