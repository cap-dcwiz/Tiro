from pathlib import Path
from typing import Optional

from tiro import Scenario
from utinni.pump import InfluxDBDataPump


class TiroTSPump(InfluxDBDataPump):
    def __init__(self, *args,
                 scenario: Scenario | str | Path,
                 uses: Optional[list[str | Path]] = None,
                 **kwargs):
        super(TiroTSPump, self).__init__(*args, **kwargs)
        uses = uses or []
        if isinstance(scenario, Scenario):
            self.scenario = scenario
            for use in uses:
                self.scenario.requires(use)
        else:
            self.scenario = Scenario.from_yaml(scenario, *uses)

    def gen_table(self, pattern, column="asset_path", agg_fn="mean"):
        paths = list(self.scenario.match_data_points(pattern))
        return super(TiroTSPump, self).gen_table(column=column, agg_fn=agg_fn, path=paths)
