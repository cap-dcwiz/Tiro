import importlib
import re
from pathlib import Path

PATH_SEP = "."


def concat_path(*components):
    return PATH_SEP.join(components).strip(PATH_SEP)


def split_path(path):
    if isinstance(path, str):
        if path:
            path = path.split(PATH_SEP)
        else:
            path = []
    return path


def snake_to_camel(name: str) -> str:
    return name
    # return "".join([x.capitalize() for x in name.split("_")])


def camel_to_snake(name: str) -> str:
    return name
    # name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    # return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


DataPointTypes = int, float, str


def load_object(loc):
    module_name, cb_name = loc.split(":")
    path = (Path(Path.cwd(), module_name + ".py"))
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, cb_name)


def prepare_scenario(scenario_path: str, uses: list[Path | str]):
    scenario = load_object(scenario_path)
    if uses:
        for use in uses:
            if isinstance(use, str):
                use = Path(use)
            scenario.requires(yaml=use.open().read())
    return scenario
