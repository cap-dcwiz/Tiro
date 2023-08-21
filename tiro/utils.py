from functools import partial

from faker import Faker
from pydantic import confloat, conint

from .core.model import Telemetry

default_faker = Faker()


class Unit:
    DEGREE_C = "degree Celsius"
    METER = "m"
    CUBIC_METER = "m^3"
    WATT = "W"
    KILO_WATT_HOUR = "kWh"
    LITRE_PER_HOUR = "L/hr"
    PSI = "psi"
    HZ = "Hz"
    WATT_PER_SQUARE_METER = "W/m^2"
    WATT_PER_SQUARE_FOOT = "W/ft^2"
    TON = "ton"


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


def RangedIntTelemetry(ge, le, unit=None, faker=default_faker) -> Telemetry:
    return Telemetry(
        conint(ge=ge, le=le),
        unit,
        faker=partial(faker.pyint, min_value=ge, max_value=le),
    )
