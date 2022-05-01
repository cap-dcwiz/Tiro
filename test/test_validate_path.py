from pathlib import Path

from tiro import Scenario
from rich import print

scenario = Scenario.from_yaml(Path("./scenario.yaml"), Path("./use1.yaml"))
mocker = scenario.mocker()

# print(scenario.model(hide_dp_values=True).schema())

data_points = list(mocker.list_data_points(skip_default=True))
# validator = scenario.validator(validate_path_only=True)
#
# with validator:
#     for path in data_points:
#         validator.collect(path, value={})
#     res = validator.validate()
#     while not res.valid:
#         for error in res.exception.errors():
#             missing_path = PATH_SEP.join(error["loc"])
#             validator.collect(missing_path, value={})
#             dp_info = scenario.query_data_point_info(scenario.asset_path_to_path(missing_path))
#             if dp_info:
#                 print("missing:", missing_path, dp_info.default_object())
#         res = validator.validate()

for path in scenario.guess_missing_paths(existing_paths=data_points):
    tags = scenario.asset_path_to_tags(path)
    print(tags | scenario.query_data_point_info(tags["path"]).default_object())
