from pathlib import Path
from pprint import pprint

from rich import print_json, print

from tiro import Scenario

scenario = Scenario.from_yaml(Path("./scenario.yaml"), Path("./use1.yaml"))
mocker = scenario.mocker()

# pprint(mocker.dict(include_data_points=False))
# pprint(mocker.dict(regenerate=True, include_data_points=False))
# print(json.dumps(mocker.dict(), indent=2))
# pprint(mocker.dict())
# pprint(mocker.dict(change_attrs=True))
# pprint(mocker.dict(regenerate=True))
#
# print_json(mocker.json(skip_default=True))
obj = mocker.dict(skip_default=True, use_default=False)
print(obj)
print_json(scenario.model(require_all_children=True).parse_obj(obj).json())
