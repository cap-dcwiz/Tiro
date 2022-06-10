import httpx
import logging

from karez.config import OptionalConfigEntity
from karez.connector import RestfulConnectorBase


class ConnectorForMockServer(RestfulConnectorBase):
    @classmethod
    def role_description(cls):
        return "Connector to fetch telemetries and attributes from a Tiro mock server."

    @classmethod
    def config_entities(cls):
        yield from super(ConnectorForMockServer, cls).config_entities()
        yield OptionalConfigEntity("by", "path", "Access data by path or uuid? (path, uuid)")

    async def fetch_data(self, client: httpx.AsyncClient, entities):
        result = []
        for entity in entities:
            if self.config.by == "path":
                r = await client.get(f"/points/{entity}")
                if r.status_code == httpx.codes.OK:
                    data = dict(path=entity, result=r.json())
                    result.append(self.update_meta(data, category=entity.split(".")[-2].lower()))
                else:
                    logging.error(f"{self.__class__.__name__}[{self.name}] request error {r.status_code}: /points/{entity}")
            elif self.config.by == "uuid":
                r = await client.get(f"/values/{entity}")
                if r.status_code == httpx.codes.OK:
                    result.append(dict(name=entity, value=r.json()))
                else:
                    logging.error(f"{self.__class__.__name__}[{self.name}] request error {r.status_code}: /values/{entity}")
            else:
                raise ValueError(f'Config entity "by" can only be "path" or "uuid"')
        return result
