from pathlib import Path
from pprint import pprint

from rich import print_json, print

from tiro import Scenario

scenario = Scenario.from_yaml(Path("./scenario.yaml"), Path("./use1.yaml"))
mocker = scenario.mocker()

obj = mocker.dict(skip_default=True, use_default=False)
print(obj)
print_json(scenario.model(require_all_children=True).parse_obj(obj).json())
