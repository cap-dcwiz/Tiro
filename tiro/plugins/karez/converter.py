from karez.converter import ConverterBase
from tiro import Scenario


class TiroConverter(ConverterBase):
    @classmethod
    def role_description(cls):
        return "Converter to format Tiro data points"

    def convert(self, payload):
        yield from Scenario.decompose_data(payload["path"], payload["result"])