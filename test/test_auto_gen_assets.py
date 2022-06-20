from pathlib import Path

from rich import print, print_json

from tiro.core import Scenario
from tiro.core.utils import decouple_uses

scenario = Scenario.from_yaml(Path("./scenario.yaml"), Path("./use1.yaml"))

print(list(decouple_uses(Path("./use1.yaml"))))
