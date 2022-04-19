import json
from pathlib import Path
from typing import Optional
from rich import print

import typer
from typer import Typer

from tiro.mock import Mocker
from ..utils import prepare_scenario

app = Typer()


@app.command("show")
def schema_show(
        scenario_path: str,
        uses: list[Path],
        output: Optional[Path] = typer.Option(None, "--output", "-o")
):
    scenario = prepare_scenario(scenario_path, uses)
    if output:
        with open(output, "w") as f:
            json.dump(scenario.model().schema(), f, indent=2)
    else:
        print(scenario.model().schema_json(indent=2))


@app.command("example")
def schema_show(
        scenario_path: str,
        uses: list[Path],
        output: Optional[Path] = typer.Option(None, "--output", "-o")
):
    scenario = prepare_scenario(scenario_path, uses)
    mocker = Mocker(scenario)
    if output:
        with open(output, 'w') as f:
            json.dump(mocker.dict(), f, indent=2)
    else:
        print(mocker.dict())
#