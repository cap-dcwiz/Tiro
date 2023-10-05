from random import shuffle

import asyncio

import httpx
from loguru import logger as logging

from karez.config import OptionalConfigEntity
from karez.connector import RestfulConnectorBase


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
            "retry", 3, "Number of retries when fetching data from the server."
        )
        yield OptionalConfigEntity(
            "shuffle", "false", "Shuffle the entities before fetching? (true, false)"
        )

    async def fetch_single(self, client: httpx.AsyncClient, entity):
        if self.config.by == "path":
            by_path = True
            url = f"/points/{entity}"
        elif self.config.by == "uuid":
            by_path = False
            url = f"/values/{entity}"
        else:
            raise ValueError(f'Config entity "by" can only be "path" or "uuid"')

        for i in range(self.config.retry):
            if i == self.config.retry - 1:
                is_last_attempt = True
            else:
                is_last_attempt = False
            try:
                r = await client.get(url)
            except Exception as e:
                self.log(
                    "exception" if is_last_attempt else "warning",
                    f"Getting {url}: {type(e)}",
                    retry_idx=i,
                )
                continue
            if r.status_code == httpx.codes.OK:
                self.log("debug", f"Getting {r.url}: {r.status_code}", retry_idx=i)
                if by_path:
                    data = dict(path=entity, result=r.json())
                    data = self.update_meta(
                        data, category=entity.split(".")[-2].lower()
                    )
                else:
                    data = dict(name=entity, value=r.json())
                return data
            else:
                self.log(
                    "error" if is_last_attempt else "warning",
                    f"Getting {r.url}: {r.status_code}",
                    retry_idx=i,
                )
            await asyncio.sleep(1)

    async def fetch_data(self, client: httpx.AsyncClient, entities):
        if self.config.shuffle.lower() == "true":
            entities = list(entities)
            shuffle(entities)
        return await asyncio.gather(*[self.fetch_single(client, e) for e in entities])
