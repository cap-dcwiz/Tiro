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

    def load_entities(self) -> list:
        return httpx.get(f"{self.config.base_url}/points/").json()