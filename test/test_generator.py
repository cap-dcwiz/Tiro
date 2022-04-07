from pprint import pprint
from random import randint

from faker import Faker
from pydantic import confloat, conint

from tiro.mock import Mocker
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
    Servers: EntityList(Server, faking_number=lambda: randint(2, 20))


class Room(Entity):
    # Telemetries
    Temperature: Telemetry(temperature_type, "°C", faker=temperature_faker)

    # Attributes
    Site: Attribute(str, faker=lambda: faker.company())

    # Entities
    Racks: EntityList(Rack, faking_number=1)
    Servers: EntityList(Server, faking_number=5)


scenario = Room()
scenario.Racks.FrontTemperature.use()
scenario.requires(
    "Site",
    "Racks.BackTemperature",
    "Racks.Servers.CPUTemperature",
    "Racks.Servers.MemoryTemperature",
    "Servers.CPUTemperature",
    "Temperature"
)

mocker = Mocker(scenario)

# pprint(mocker.dict(include_data_points=False))
# pprint(mocker.dict(regenerate=True, include_data_points=False))
pprint(mocker.dict())
# pprint(mocker.dict())
# pprint(mocker.dict(change_attrs=True))
# pprint(mocker.dict(regenerate=True))
#
# print(mocker.gen_data_points(f"{mocker.list_entities()[0]}/site"))
# print(mocker.gen_data_points(f"{mocker.list_entities()[0]}/site"))
# print(mocker.gen_data_points(f"{mocker.list_entities()[0]}/site", change_attr=True))
# print(mocker.gen_data_points(f"{mocker.list_entities()[1]}/front_temperature"))
#
# print(scenario.model().parse_obj(mocker.dict()).json(indent=2))
#
# pprint(mocker.list_data_points())
