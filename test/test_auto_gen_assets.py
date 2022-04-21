from pathlib import Path

from rich import print, print_json

from tiro import Scenario

scenario = Scenario.from_yaml(Path("./scenario.yaml"), Path("./use1.yaml"))

# print_json(scenario.model(hide_data_points=False).schema_json())
print(scenario.mocker().dict())
