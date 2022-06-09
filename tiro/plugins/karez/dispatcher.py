import httpx as httpx

from karez.config import OptionalConfigEntity
from karez.dispatcher import DispatcherBase


class DispatcherForMockServer(DispatcherBase):
    @classmethod
    def role_description(cls) -> str:
        return "Dispatcher for Tiro Mock server"

    @classmethod
    def config_entities(cls):
        yield from super(DispatcherForMockServer, cls).config_entities()
        yield OptionalConfigEntity("base_url", "http://localhost:8000", "URL of the Tiro Mock Server")
        yield OptionalConfigEntity("by", "path", "Access data by path or uuid? (path, uuid)")

    def load_entities(self) -> list:
        if self.config.by == "path":
            url = f"{self.config.base_url}/points/"
        elif self.config.by == "uuid":
            url = f"{self.config.base_url}/values/"
        else:
            raise ValueError(f'Config entity "by" can only be "path" or "uuid"')
        return httpx.get(url).json()
