from arango import ArangoClient
from rich import print

from tiro.plugins.graphdb import ArangoAgent
from tiro.core.utils import prepare_scenario

scenario = prepare_scenario("scenario:scenario", uses=["./use1.yaml"])

gdb_client = ArangoAgent(scenario, "tiro_test", "scenario",
                         ArangoClient(hosts="http://localhost:8529"),
                         auth_info=dict(password="12345678"))

data = gdb_client.capture_status(pattern=".*Server%(CPU|Memory)Temperature")
print(data)
