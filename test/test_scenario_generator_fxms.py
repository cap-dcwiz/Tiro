from sys import argv

from tiro.utils.scenario_generator import Asset, GPTPointGenerator, Point
from rich import print

root = Asset("System", "ESS_system")
for i in range(1, 4):
    rack = root.add_asset("Rack", f"Rack_{i:02}")
    for dp in ("AD", "SR"):
        for j in range(1, 4):
            for cond in ("Past", "Present"):
                rack.add_point(f"{dp}Plot{j}{cond}", 0, 1)
    for j in range(1, 10 if i < 3 else 11):
        module = rack.add_asset("Module", f"{rack.name}_Module_{j:02}")
        for k in range(1, 21 if i < 3 else 19):
            module.add_asset("Cell", f"{module.name}_Cell_{k:02}")

gpt_helper = GPTPointGenerator(root, token=argv[1], country="Singapore", model="gpt-4", asset="Battery System")
gpt_helper.add_path("Rack.SoC", "%")
gpt_helper.add_path("Rack.Module.SoC", "%")
gpt_helper.add_path("Rack.Module.Temperature", "°C")
gpt_helper.add_path("Rack.Module.Cell.Reliability", "%")
gpt_helper.add_path("Rack.Module.Cell.Risk", "°C")
gpt_helper.add_path("Rack.Module.Cell.Temperature", "°C")
gpt_helper.add_path("Rack.Module.Cell.SoC", "%")
gpt_helper.add_path("Rack.Module.Cell.SoH", "%")
gpt_helper.complete_asset()

print(root.to_reference(as_yaml=True))
print(root.to_schema(as_yaml=True))
print(root.to_uses(as_yaml=True))
