from pathlib import Path
from random import randint

from faker import Faker
from pydantic import confloat, conint

from tiro import Scenario
from tiro.core.mock import MockApp
from tiro.core.model import Entity, Telemetry, Attribute, EntityList



scenario = Scenario.from_yaml(Path("./scenario.yaml"), Path("./use1.yaml"))
app = MockApp(scenario.mocker())
