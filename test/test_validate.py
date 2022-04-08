import json
import time
from pprint import pprint
from random import randint, choice

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

# mocker = Mocker(scenario)
#
# data_points = list(mocker.list_data_points())
#
# with Validator(scenario, retention=1) as validator:
#     for _ in range(2000):
#         path = choice(data_points)
#         value = mocker.gen_data_point(path)
#         validator.collect(path, value)
#         time.sleep(0.001)
#     validator.validate(verbose=True)
