import pandas as pd

from tiro.utils.scenario_generator import Asset, Point
from rich import print

root = Asset.from_snapshot(pd.read_csv("snapshot.csv"))

print(root.to_reference(as_yaml=True))
# print(root.to_schema(as_yaml=True))
# print(root.to_uses(as_yaml=True))
# print(root.all_point_path())
