from random import randint, choice
from rich import print_json, print

from faker import Faker
from pydantic import confloat, conint

from tiro.mock import Mocker
from tiro.validate import Validator
from tiro.vocabulary import Entity, Telemetry, Attribute, EntityList

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

# print(mocker.dict())

print(list(scenario.decompose_data("rack.4a248aea-b96a-11ec-90b6-aa966665d395.server.4a248cb6-b96a-11ec-90b6-aa966665d395.telemetry.cpu_temperature", dict(A=2))))

# print(mocker.dict())
#
# for item in scenario.decompose_data("", mocker.dict()):
#     print(item["path"])

for path in scenario.match_data_points(r"#%Server#CPUTemperature"):
    print(path)