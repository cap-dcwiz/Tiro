from pathlib import Path

from tiro import Scenario
from rich import print

scenario = Scenario.from_yaml(Path("./scenario.yaml"), Path("./use1.yaml"))
mocker = scenario.mocker()

data_points = list(mocker.list_data_points(skip_default=True))

for path in scenario.guess_missing_paths(existing_paths=data_points):
    tags = scenario.data_point_path_to_tags(path)
    print(tags | scenario.query_data_point_info(tags["path"]).default_object())
