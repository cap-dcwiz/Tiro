from pathlib import Path
from typing import Optional

import httpx
import time
import typer
import uvicorn
from rich import print

from tiro.core import Scenario
from tiro.core.mock import MockApp

app = typer.Typer()


@app.command("serve")
def mock(
    scenario_path: Path,
    uses: list[Path],
    host: Optional[str] = typer.Option("127.0.0.1", "--host", "-h"),
    port: Optional[int] = typer.Option(8000, "--port", "-p"),
    skip_defaults: Optional[bool] = typer.Option(True, "--skip-defaults", "-s"),
    use_defaults: Optional[bool] = typer.Option(True, "--use-defaults", "-u"),
    reference: Optional[Path] = typer.Option(None, "--reference", "-r"),
):
    scenario = Scenario.from_yaml(scenario_path, *uses)
    mock_app = MockApp(
        scenario.mocker(reference=reference),
        skip_defaults=skip_defaults,
        use_defaults=use_defaults,
    )
    uvicorn.run(mock_app, host=host, port=port)


@app.command("push")
def push(
    collect_interval: int = 60,
    data_ssl: bool = typer.Option(False, "-data-ssl", "-a"),
    data_address: str = typer.Option("127.0.0.1:8000", "--data-addr", "-d"),
    receiver_ssl: bool = typer.Option(False, "-reveiver-ssl", "-e"),
    receiver_address: str = typer.Option("127.0.0.1:8001", "--recv-addr", "-r"),
):
    while True:
        data_url = f"http{'s' if data_ssl else ''}://{data_address}"
        receiver_url = f"http{'s' if receiver_ssl else ''}://{receiver_address}"
        r = httpx.get(f"{data_url}/points/")
        print(r)
        for path in r.json():
            r = httpx.get(f"{data_url}/points/{path}")
            print(f"Forwarding {path}")
            r = httpx.post(f"{receiver_url}/points/{path}", json=r.json())
        time.sleep(collect_interval)
