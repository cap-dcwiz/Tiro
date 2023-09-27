from tiro.utils.scenario_generator import Asset, Point
from rich import print

root = Asset("DataCenter", "DC1")
data_hall = root.add_asset("DataHall", "Room 1")
acu = data_hall.add_asset("ACU", "ACU1")
acu.SupplyTemperature = Point(10, 20)
acu.ReturnTemperature = Point(20, 30)
acu.FanSpeed = Point(100, 200)

for rack_id in range(1, 3):
    rack = data_hall.add_asset("Rack", f"Rack{rack_id}")
    for server_id in range(1, 3):
        server = rack.add_asset("Server", f"Server {rack_id}_{server_id}")
        server.Power = Point(100, 200)
        server.Temperature = Point(20, 30)


root["DataHall"]["Room 1"]["Rack"]["Rack1"].Power = Point(100, 200)

print(root.to_reference(as_yaml=True))
print(root.to_schema(as_yaml=True))
print(root.to_uses(as_yaml=True))
