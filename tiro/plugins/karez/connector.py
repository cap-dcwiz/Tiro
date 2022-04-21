from karez.connector import RestfulConnectorBase


class ConnectorForMockServer(RestfulConnectorBase):
    @classmethod
    def role_description(cls):
        return "Connector to fetch telemetries and attributes from a Tiro mock server."

    async def fetch_data(self, client, entities):
        for entity in entities:
            r = await client.get(f"/points/{entity}")
            data = dict(path=entity, result=r.json())
            return [self.update_meta(data, category=entity.split(".")[-2].lower())]