from pprint import pprint
from random import randint

from faker import Faker
from pydantic import confloat, conint

from tiro.core.mock import Mocker
from tiro.core.model import Entity, Telemetry, Attribute, EntityList

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
    Site: Attribute(str, faker=lambda: faker.company())

    # Entities
    Rack: EntityList(Rack, faking_number=1)
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

pprint(mocker.dict(include_data_points=False))
# pprint(mocker.dict(regenerate=True, include_data_points=False))
# print(json.dumps(mocker.dict(), indent=2))
# pprint(mocker.dict())
# pprint(mocker.dict(change_attrs=True))
# pprint(mocker.dict(regenerate=True))
#
print(scenario.model().parse_obj(mocker.dict()).json(indent=2))