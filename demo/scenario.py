from random import randint

from faker import Faker
from pydantic import confloat

from tiro.assets.data_hall import ServerBase, RackBase, RoomBase
from tiro.core.model import EntityList

temperature_type = confloat(ge=0, le=50)
faker = Faker()


def temperature_faker():
    return faker.pyfloat(right_digits=2, min_value=10, max_value=30)


class Server(ServerBase):
    pass


class Rack(RackBase):
    # Entities
    Server: EntityList(Server, faking_number=lambda: randint(2, 5))


class Room(RoomBase):
    # Entities
    Rack: EntityList(Rack, faking_number=1)
    Server: EntityList(Server, faking_number=1)


scenario = Room()
