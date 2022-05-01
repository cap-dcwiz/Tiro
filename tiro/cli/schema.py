import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from rich import print

import typer
from typer import Typer

from tiro.core import Scenario

app = Typer()


def json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


@app.command("show")
def schema_show(
        scenario_path: Path,
        uses: list[Path],
        output: Optional[Path] = typer.Option(None, "--output", "-o"),
        all_children: Optional[bool] = typer.Option(True, "--all-children", "-a",
                                                    help="Require all claimed children for each asset")
):
    scenario = Scenario.from_yaml(scenario_path, *uses)
    if output:
        with open(output, "w") as f:
            json.dump(scenario.model().schema(), f, indent=2, default=json_default)
    else:
        print(scenario.model(require_all_children=all_children).schema_json(indent=2))


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
