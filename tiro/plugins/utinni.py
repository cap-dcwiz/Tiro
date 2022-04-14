from tiro.utils import prepare_scenario
from utinni.pump import InfluxDBDataPump


class TiroTSPump(InfluxDBDataPump):
    def __init__(self, *args, scenario=None, scenario_path=None, uses=None, **kwargs):
        super(TiroTSPump, self).__init__(*args, **kwargs)
        if scenario:
            self.scenario = scenario
        else:
            if not scenario_path:
                raise RuntimeError("Either scenario or scenario_path must be specified.")
            self.scenario = prepare_scenario(scenario_path, uses)

    def gen_table(self, pattern, column="asset_path", agg_fn="mean"):
        paths = list(self.scenario.match_data_points(pattern))
        return super(TiroTSPump, self).gen_table(column=column, agg_fn=agg_fn, path=paths)
