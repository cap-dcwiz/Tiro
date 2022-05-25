from pathlib import Path

from rich import print as rprint
from tiro.core import Scenario
from tiro.plugins.graph.agent import ArangoAgent
from tiro.plugins.graph.qpath import QueryPath

query = """
Room:
    $name_match: 7c5a8382
    Site:
        $match: Arnold
    Rack:
        FrontTemperature: 
            $gt: 20
            $le: 25
        BackTemperature:
        Server:
            CPUTemperature:
            _MemoryTemperature:
                $gt: 20
    Server:
        CPUTemperature:
        MemoryTemperature:
            $gt: 20
    Temperature:
"""


root_path = QueryPath.parse(query)

print(root_path.all_fields())

print(root_path.all_path_str(exclude_intermediate=False))

scenario = Scenario.from_yaml(Path("./scenario.yaml"),
                              Path("./use1.yaml"))
gdb_client = ArangoAgent(scenario,
                         db_name="tiro_test",
                         graph_name="scenario",
                         hosts="http://localhost:8529",
                         auth_info=dict(password="arangodb_password")
                         )

rprint(gdb_client.query_by_qpath(query, value_only=True, as_dataframe=True).columns)
# print(gdb_client.query_by_regex("Room%Server%MemoryTemperature",
#                                 value_only=True,
#                                 as_dataframe=True))
