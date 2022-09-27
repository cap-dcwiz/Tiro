from functools import partial

from faker import Faker
from pydantic import confloat

from tiro.core import Entity
from tiro.core.model import Telemetry

default_faker = Faker()


def RangedFloatTelemetry(
        ge, le, unit=None, right_digits=2, faker=default_faker
) -> Telemetry:
    return Telemetry(
        confloat(ge=ge, le=le),
        unit,
        faker=partial(
            faker.pyfloat, right_digits=right_digits, min_value=ge, max_value=le
        ),
    )


class DataHall(Entity):
    """Data hall asset."""
    RoomTemperature = RangedFloatTelemetry(-50, 50)
    ChilledWaterSupplyTemperature = RangedFloatTelemetry(0, 1000)
    ChilledWaterReturnTemperature = RangedFloatTelemetry(0, 1000)


class Rack(Entity):
    ActivePower: RangedFloatTelemetry(0, 1000)
    FrontTemperatures: RangedFloatTelemetry(0, 60)
    BackTemperature: RangedFloatTelemetry(0, 60)
    Temperature: RangedFloatTelemetry(0, 60)


class Server(Entity):
    ActivePower: RangedFloatTelemetry(0, 1000)
    HeatLoad: RangedFloatTelemetry(0, 1000)
    FlowRate: RangedFloatTelemetry(0, 1000)
    CPUTemperature: RangedFloatTelemetry(0, 150)


class CRAC(Entity):
    ActivePower: RangedFloatTelemetry(0, 1000)
    SupplyTemperature: RangedFloatTelemetry(0, 50)
    ReturnTemperature: RangedFloatTelemetry(0, 50)
    FanSpeed: RangedFloatTelemetry(0, 1000)
