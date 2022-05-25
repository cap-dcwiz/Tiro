import json
from pathlib import Path
from rich import print

import typer
import uvicorn

from tiro.core import Scenario
from tiro.core.validate import RestfulValidationApp

app = typer.Typer()


@app.command("serve")
def serve(
        scenario_path: Path,
        uses: list[Path],
        host: str = typer.Option("127.0.0.1", "--host", "-h"),
        port: int = typer.Option(8001, "--port", "-p"),
        log_size: int = typer.Option(10, "--log-size", "-l"),
        retention: int = typer.Option(60, "--retention", "-r")
):
    print(f"[green]CONF[/green]:     Retention: {retention}")
    print(f"[green]CONF[/green]:     Log Size: {log_size}")
    scenario = Scenario.from_yaml(scenario_path, *uses)
    validator = scenario.validator(retention=retention, log=True, log_size=log_size)
    validate_app = RestfulValidationApp(validator)
    uvicorn.run(validate_app, host=host, port=port)


@app.command("test")
def test(
        scenario_path: Path,
        uses: list[Path],
        input: Path
):
    scenario = Scenario.from_yaml(scenario_path, *uses)
    validator = scenario.validator(log=True)
    context = json.load(input.open())
    res = validator.validate_dict(context)
    if res.valid:
        print("[green]Validation succeeded![/green]")
    else:
        print("[red]Validation failed![/red]")
        print(res.exception)
