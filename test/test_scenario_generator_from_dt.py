from tiro.utils.scenario_generator import Asset, Point
from rich import print

root = Asset("DataCenter", "DC1")
root.load_room_from_dt("test/rack_20_acu_1_mixed.json")
root.load_room_from_dt("test/rack_16_acu_1_hot_mixed.json")

for sensor in root["DataHall.Sensor"].values():
    sensor.Temperature = Point(0, 100)

# Or
root["DataHall.Sensor.Humidity"] = Point(0, 100)
root.PUE = Point(1.3, 1.5)

chiller_plant = root.add_asset("ChillerPlant", "CP1")
chiller_plant.COP = Point(5, 8)

for i in range(1, 7):
    chiller_plant.add_asset("Chiller", f"CHILLER-{i}")
    chiller_plant.add_asset("CoolingTower", f"CT-{i}")
    chiller_plant.add_asset("ChilledWaterPump", f"CWP-{i}")
    chiller_plant.add_asset("CondenserWaterPump", f"CWP-{i}")

chiller_plant["Chiller.Power"] = Point(0, 500)
chiller_plant["Chiller.ChilledWaterSupplyTemperature"] = Point(10, 20)
chiller_plant["Chiller.ChilledWaterReturnTemperature"] = Point(20, 30)
chiller_plant["Chiller.ChilledWaterFlowRate"] = Point(200, 300)
chiller_plant["Chiller.CondenserWaterSupplyTemperature"] = Point(0, 100)
chiller_plant["Chiller.CondenserWaterReturnTemperature"] = Point(0, 100)
chiller_plant["Chiller.CondenserWaterFlowRate"] = Point(0, 100)

chiller_plant["CoolingTower.Power"] = Point(0, 100)
chiller_plant["CoolingTower.CoolingWaterSupplyTemperature"] = Point(0, 100)
chiller_plant["CoolingTower.CoolingWaterReturnTemperature"] = Point(0, 100)
chiller_plant["CoolingTower.CoolingWaterFlowRate"] = Point(0, 100)

chiller_plant["ChilledWaterPump.Power"] = Point(0, 100)
chiller_plant["ChilledWaterPump.FlowRate"] = Point(0, 100)
chiller_plant["ChilledWaterPump.Pressure"] = Point(0, 100)
chiller_plant["ChilledWaterPump.VSDSpeed"] = Point(0, 100)

chiller_plant["CondenserWaterPump.Power"] = Point(0, 100)
chiller_plant["CondenserWaterPump.FlowRate"] = Point(0, 100)
chiller_plant["CondenserWaterPump.Pressure"] = Point(0, 100)
chiller_plant["CondenserWaterPump.VSDSpeed"] = Point(0, 100)

print(root.to_reference(as_yaml=True))
print(root.to_schema(as_yaml=True))
print(root.to_uses(as_yaml=True))
