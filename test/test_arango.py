from pathlib import Path

from arango import ArangoClient
from rich import print

from tiro.core import Scenario
from tiro.plugins.arango import ArangoAgent

scenario = Scenario.from_yaml(Path("./scenario.yaml"), Path("./use1.yaml"))
gdb_client = ArangoAgent(scenario,
                         db_name="tiro_test3",
                         graph_name="scenario",
                         hosts="http://localhost:8529",
                         auth_info=dict(password="arangodb_password")
                         )

gdb_client.create_graph(clear_existing=True, clear_database=True)
for item in scenario.decompose_data("", scenario.mocker().dict(skip_default=True)):
    gdb_client.update(item)

# data = gdb_client.capture_status()
# print(scenario.model().parse_obj(data).json(indent=2))

data = gdb_client.capture_status()
print(data)
