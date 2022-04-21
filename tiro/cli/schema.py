import json
from pathlib import Path
from typing import Optional
from rich import print

import typer
from typer import Typer

from tiro import Scenario
from tiro.core.mock import Mocker

app = Typer()


@app.command("show")
def schema_show(
        scenario_path: Path,
        uses: list[Path],
        output: Optional[Path] = typer.Option(None, "--output", "-o")
):
    scenario = Scenario.from_yaml(scenario_path, *uses)
    if output:
        with open(output, "w") as f:
            json.dump(scenario.model().schema(), f, indent=2)
    else:
        print(scenario.model().schema_json(indent=2))


@app.command("example")
def schema_example(
        scenario_path: Path,
        uses: list[Path],
        output: Optional[Path] = typer.Option(None, "--output", "-o")
):
    scenario = Scenario.from_yaml(scenario_path, *uses)
    mocker = scenario.mocker()
    if output:
        with open(output, 'w') as f:
            json.dump(mocker.dict(), f, indent=2)
    else:
        print(mocker.dict())
#