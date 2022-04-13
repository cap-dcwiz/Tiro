from datetime import timedelta

from dynaconf import Dynaconf

from tiro.plugins.utinni import TiroTSPump
from utinni import Context

conf = Dynaconf(settings_files=["./utinni_config.toml"])

context = Context(**conf.on_request)

context.add_pump("tiro",
                 TiroTSPump(scenario_path="scenario:scenario",
                            uses=["use1.yaml"],
                            **conf.influxdb))

table = context.tiro_table(".*Server%(CPU|Memory)Temperature", column="Server")

context.bind(start=-timedelta(hours=1),
             step=timedelta(minutes=10))
print(table["MemoryTemperature"].value)
