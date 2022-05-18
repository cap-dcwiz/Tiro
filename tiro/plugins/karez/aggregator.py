import json
from datetime import datetime
from pathlib import Path

from arango import ArangoClient
from rich import print, print_json

from karez.aggregator.base import AggregatorBase
from karez.config import ConfigEntity, OptionalConfigEntity
from tiro.core import Scenario
from tiro.core.validate import Validator
from tiro.plugins.arango import ArangoAgent


class ArangoAggregator(AggregatorBase):
    def __init__(self, *args, **kwargs):
        super(ArangoAggregator, self).__init__(*args, **kwargs)
        self._agent = None

    @classmethod
    def role_description(cls):
        return "Aggregator to send Tiro data to ArangoDB"

    def config_entities(self):
        yield from super(ArangoAggregator, self).config_entities()
        yield ConfigEntity("scenario", "Scenario file")
        yield ConfigEntity("uses", "Configuration files for use cases")
        yield ConfigEntity("db_name", "Database name")
        yield ConfigEntity("graph_name", "Graph name")
        yield OptionalConfigEntity("hosts", "http://localhost:8529",
                                   "Host URL or list of URLs (coordinators in a cluster)")
        yield OptionalConfigEntity("auth", {}, "Authentication args for connecting to db")

    @property
    def agent(self):
        if not self._agent:
            uses = map(Path, self.config.uses.split(","))
            scenario = Scenario.from_yaml(Path(self.config.scenario), *uses)
            self._agent = ArangoAgent(scenario,
                                      db_name=self.config.db_name,
                                      graph_name=self.config.graph_name,
                                      client=ArangoClient(hosts=self.config.hosts),
                                      auth_info=self.config.auth)
            self._agent.create_graph(clear_database=False, clear_existing=False)
        return self._agent

    def process(self, payload):
        self.agent.create_graph(clear_existing=False, clear_database=False)
        self.agent.update(payload)


class ValidationAggregator(AggregatorBase):
    def __init__(self, *args, **kwargs):
        super(ValidationAggregator, self).__init__(*args, **kwargs)
        self.validator = None
        self.last_validation_start_time = datetime.min

    @classmethod
    def role_description(cls) -> str:
        return "Aggregator for validating the Tiro data"

    @classmethod
    def config_entities(cls):
        yield from super(ValidationAggregator, cls).config_entities()
        yield OptionalConfigEntity("scenario", None,
                                   "Scenario file (either scenario/uses or schema file must be provided)")
        yield OptionalConfigEntity("uses", None, "Configuration files for use cases")
        yield OptionalConfigEntity("Schema", None,
                                   "JSON Schema file (either scenario/uses or schema file must be provided)")
        yield OptionalConfigEntity("retention", 60, "Time window to receive data points")
        yield OptionalConfigEntity("log_file", None, "Log file to record validation results")

    def process(self, payload):
        if not self.validator:
            if self.config.scenario:
                uses = map(Path, self.config.uses.split(","))
                scenario = Scenario.from_yaml(Path(self.config.scenario), *uses)
                self.validator = scenario.validator(retention=self.config.retention, log=False)
            else:
                with open(self.config.schema, "r") as f:
                    schema = json.load(f)
                self.validator = Validator(schema=schema, retention=self.config.retention, log=False)
        self.validator.collect(payload["path"], payload["result"])
        print(f"[bold]\[{self.TYPE}-{self.name}][/bold] "
              f"Collection size: {self.validator.current_collection_size}",
              end="\r")
        if self.validator.last_validation_start_time > self.last_validation_start_time:
            result = self.validator.log[0].json()
            print()
            print_json(result)
            if self.config.log_file:
                with open(self.config.log_file, "a") as f:
                    f.write(result)
                    f.write("\n")
            self.last_validation_start_time = self.validator.last_validation_start_time