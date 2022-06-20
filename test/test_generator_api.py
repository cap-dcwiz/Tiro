from pathlib import Path
from tiro import Scenario
from tiro.core.mock import MockApp

scenario = Scenario.from_yaml(Path("./scenario.yaml"), Path("./use1.yaml"))
app = MockApp(scenario.mocker())
