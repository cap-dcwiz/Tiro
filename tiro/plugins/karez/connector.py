from random import shuffle

import asyncio

import httpx

from karez.config import OptionalConfigEntity
from karez.connector import RestfulConnectorBase

from karez.utils import generator_to_list


class ConnectorForMockServer(RestfulConnectorBase):
    @classmethod
    def role_description(cls):
        return "Connector to fetch telemetries and attributes from a Tiro mock server."

    @classmethod
    def config_entities(cls):
        yield from super(ConnectorForMockServer, cls).config_entities()
        yield OptionalConfigEntity(
            "by", "path", "Access data by path or uuid? (path, uuid)"
        )
        yield OptionalConfigEntity(
            "shuffle", "false", "Shuffle the entities before fetching? (true, false)"
        )

    async def fetch_single(self, client: httpx.AsyncClient, entity):
        if self.config.by == "path":
            body = await self.try_request(client, f"/points/{entity}")
            if body:
                return self.update_meta(
                    dict(path=entity, result=body),
                    category=entity.split(".")[-2].lower(),
                )
        elif self.config.by == "uuid":
            body = await self.try_request(client, f"/values/{entity}")
            if body:
                return dict(name=entity, value=body)
        else:
            raise ValueError(f'Config entity "by" can only be "path" or "uuid"')

    @generator_to_list
    async def fetch_data(self, client: httpx.AsyncClient, entities):
        if self.config.shuffle.lower() == "true":
            entities = list(entities)
            shuffle(entities)
        for item in await asyncio.gather(
            *[self.fetch_single(client, e) for e in entities]
        ):
            if item is not None:
                yield item
