from pathlib import Path
from random import choice

from tiro import Scenario
from tiro.core.validate import Validator

scenario = Scenario.from_yaml(Path("./scenario.yaml"), Path("./use1.yaml"))
mocker = scenario.mocker()

data_points = list(mocker.list_data_points())

with Validator(schema=scenario.model().schema(), retention=1) as validator:
    for i in range(10):
        path = choice(data_points)
        value = mocker.gen_data_point(path)
        validator.collect(path, value)
        # time.sleep(0.0005)
    res = validator.validate()
    print(res)
