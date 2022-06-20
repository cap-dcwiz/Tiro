from pathlib import Path
from random import choice

from rich import print_json

from tiro.core import Scenario
from tiro.core.validate import Validator

scenario = Scenario.from_yaml(Path("./scenario.yaml"), Path("./use1.yaml"))
mocker = scenario.mocker()

data_points = list(mocker.list_data_points(skip_default=True))

with scenario.validator(require_all_children=True, retention=1) as validator:
    for path in data_points:
        value = mocker.gen_data_point(path)
        print(path, value)
        validator.collect(path, value)
    res = validator.validate()
    print(res)

print_json(scenario.model(require_all_children=False).schema_json())
