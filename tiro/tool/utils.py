import importlib
from pathlib import Path

from tiro.vocabulary import Entity


def load_object(loc):
    module_name, cb_name = loc.split(":")
    path = (Path(Path.cwd(), module_name + ".py"))
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, cb_name)


def prepare_scenario(scenario_path: str, uses: list[Path]):
    scenario: Entity = load_object(scenario_path)
    if uses:
        for use in uses:
            scenario.requires(yaml=use.open().read())
    return scenario
