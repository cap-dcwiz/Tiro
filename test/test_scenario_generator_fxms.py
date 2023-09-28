from sys import argv

from tiro.utils.scenario_generator import Asset, GPTPointGenerator
from rich import print

root = Asset("System", "ESS_system")
for i in range(1, 4):
    rack = root.add_asset("Rack", f"Rack_{i:02}")
    for j in range(1, 10 if i < 3 else 11):
        module = rack.add_asset("Module", f"{rack.name}_Module_{j:02}")

gpt_helper = GPTPointGenerator(root, token=argv[1], country="Singapore", model="gpt-4", asset="Battery System")
gpt_helper.add_path("Rack.Module.ModuleSoC", "%")
gpt_helper.add_path("Rack.Module.ModuleTemperature", "°C")
gpt_helper.complete_asset()

print(root.to_reference(as_yaml=True))
print(root.to_schema(as_yaml=True))
print(root.to_uses(as_yaml=True))
