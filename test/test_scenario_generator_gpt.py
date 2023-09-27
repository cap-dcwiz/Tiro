from tiro.utils.scenario_generator import Asset, GPTPointGenerator
from rich import print
from sys import argv

root = Asset("DataCenter", "DC1")
data_hall = root.add_asset("DataHall", "Room 1")
data_hall.add_asset("ACU", "ACU 1")
data_hall.add_asset("ACU", "ACU 2")

for rack_id in range(1, 3):
    rack = data_hall.add_asset("Rack", f"Rack {rack_id}")
    for server_id in range(1, 5):
        server = rack.add_asset("Server", f"Server {rack_id}_{server_id}")

gpt_helper = GPTPointGenerator(token=argv[1], country="Singapore", model="gpt-4")
gpt_helper.add_path("DataHall.ACU.SupplyTemperature", "°C")
gpt_helper.add_path("DataHall.ACU.ReturnTemperature", "°C")
gpt_helper.add_path("DataHall.ACU.FanSpeed", "Hz")
gpt_helper.add_path("DataHall.Rack.Power", "W")
gpt_helper.add_path("DataHall.Rack.Server.Power", "W")
gpt_helper.add_path("DataHall.Rack.Server.Temperature", "°C")
gpt_helper.add_path("DataHall.Rack.Server.Humidity", "%")
gpt_helper.add_path("DataHall.Rack.Server.CPUUtilization", "%")
gpt_helper.complete_asset(root)

print(root.to_reference(as_yaml=True))
