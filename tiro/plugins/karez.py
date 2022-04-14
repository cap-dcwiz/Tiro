from datetime import datetime

import httpx as httpx
from arango import ArangoClient
from rich import print, print_json

from karez.aggregator.base import AggregatorBase
from karez.config import OptionalConfigEntity, ConfigEntity
from karez.connector import RestfulConnectorBase
from karez.converter import ConverterBase
from karez.dispatcher import DispatcherBase
from tiro.graphdb import ArangoAgent
from tiro.utils import prepare_scenario
from tiro.validate import Validator
from tiro.vocabulary import Entity


class DispatcherForMockServer(DispatcherBase):
    @classmethod
    def role_description(cls) -> str:
        return "Dispatcher for Tiro Mock server"

    @classmethod
    def config_entities(cls):
        yield from super(DispatcherForMockServer, cls).config_entities()
        yield OptionalConfigEntity("base_url", "http://localhost:8000", "URL of the Tiro Mock Server")

    def load_entities(self) -> list:
        return httpx.get(f"{self.config.base_url}/points/").json()


class ConnectorForMockServer(RestfulConnectorBase):
    @classmethod
    def role_description(cls):
        return "Connector to fetch telemetries and attributes from a Tiro mock server."

    async def fetch_data(self, client, entities):
        for entity in entities:
            r = await client.get(f"/points/{entity}")
            return [dict(path=entity, result=r.json())]


class TiroConverter(ConverterBase):
    @classmethod
    def role_description(cls):
        return "Converter to format Tiro data points"

    def convert(self, payload):
        yield from Entity.decompose_data(payload["path"], payload["result"])


class Tiro2ArangoAggregator(AggregatorBase):
    def __init__(self, *args, **kwargs):
        super(Tiro2ArangoAggregator, self).__init__(*args, **kwargs)
        self._agent = None

    @classmethod
    def role_description(cls):
        return "Aggregator to send Tiro data to ArangoDB"

    def config_entities(self):
        yield from super(Tiro2ArangoAggregator, self).config_entities()
        yield ConfigEntity("scenario", "Scenario file")
        yield ConfigEntity("uses", "Configuration files for use cases")
        yield ConfigEntity("db_name", "Database name")
        yield ConfigEntity("graph_name", "Graph name")
        yield OptionalConfigEntity("hosts", "http://localhost:8529",
                                   "Host URL or list of URLs (coordinators in a cluster)")
        yield OptionalConfigEntity("db_auth_args", {}, "Authentication args for connecting to db")

    @property
    def agent(self):
        if not self._agent:
            uses = self.config.uses.split(",")
            scenario = prepare_scenario(self.config.scenario, uses)
            self._agent = ArangoAgent(scenario,
                                      self.config.db_name,
                                      self.config.graph_name,
                                      ArangoClient(hosts=self.config.hosts))
            self._agent.create_graph(clear_database=False, clear_existing=False)
        return self._agent

    def process(self, payload):
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
        yield ConfigEntity("scenario", "Scenario file")
        yield ConfigEntity("uses", "Configuration files for use cases")
        yield OptionalConfigEntity("retention", 60, "Time window to receive data points")
        yield OptionalConfigEntity("log_file", None, "Log file to record validation results")

    def process(self, payload):
        if not self.validator:
            uses = self.config.uses.split(",")
            scenario = prepare_scenario(self.config.scenario, uses)
            self.validator = Validator(scenario, retention=self.config.retention, log=False)
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
            self.last_validation_start_time = self.validator.last_validation_start_time
