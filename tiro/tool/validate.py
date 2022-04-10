from pathlib import Path
from rich import print

import typer
import uvicorn

from tiro.tool.utils import prepare_scenario
from tiro.validate import ValidationApp, Validator

app = typer.Typer()


@app.command("serve")
def serve(
        scenario_path: str,
        uses: list[Path],
        host: str = typer.Option("127.0.0.1", "--host", "-h"),
        port: int = typer.Option(8001, "--port", "-p"),
        log_size: int = typer.Option(10, "--log-size", "-l"),
        retention: int = typer.Option(60, "--retention", "-r")
):
    print(f"[green]CONF[/green]:     Retention: {retention}")
    print(f"[green]CONF[/green]:     Log Size: {log_size}")
    scenario = prepare_scenario(scenario_path, uses)
    validator = Validator(scenario, retention=retention, log=True, log_size=log_size)
    validate_app = ValidationApp(validator)
    uvicorn.run(validate_app, host=host, port=port)
