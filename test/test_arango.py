from pathlib import Path

from arango import ArangoClient
from rich import print

from tiro import Scenario
from tiro.plugins.arango import ArangoAgent

scenario = Scenario.from_yaml(Path("./scenario.yaml"), Path("./use1.yaml"))
gdb_client = ArangoAgent(scenario, "tiro_test", "scenario",
                         ArangoClient(hosts="http://localhost:8529"))

# gdb_client.create_graph(clear_existing=True, clear_database=True)
# for item in scenario.decompose_data("", mocker.dict()):
#     gdb_client.update(item)

# data = gdb_client.capture_status()
# print(scenario.model().parse_obj(data).json(indent=2))

data = gdb_client.capture_status(pattern=".*Server%(CPU|Memory)Temperature")
print(data)
