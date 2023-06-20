import os

from pathlib import Path
from typing import Optional

import typer
import yaml

from rich import print

from tiro.core.draft import DraftGenerator

app = typer.Typer()


@app.command("scenario")
def gen_schema(
    csv_file: Path,
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
    asset_library: Optional[Path] = typer.Option(None, "--asset-library", "-l"),
):
    draft_gen = DraftGenerator(csv_file=csv_file)
    schema = draft_gen.schema
    if asset_library:
        asset_library = str(asset_library)
        if os.sep in asset_library:
            name = asset_library.split(os.sep)[-1]
            path = os.sep.join(asset_library.split(os.sep)[:-1])
        else:
            name = asset_library
            path = None
        schema["$asset_library_name"] = name
        if path:
            schema["$asset_library_path"] = path
    out = yaml.dump(schema)
    if output:
        with open(output, "w") as f:
            f.write(out)
    else:
        print(out)


@app.command("uses")
def gen_uses(
    csv_file: Path,
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
):
    draft_gen = DraftGenerator(csv_file=csv_file)
    out = yaml.dump(draft_gen.uses)
    if output:
        with open(output, "w") as f:
            f.write(out)
    else:
        print(out)


@app.command("reference")
def gen_reference(
    csv_file: Path,
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
):
    draft_gen = DraftGenerator(csv_file=csv_file)
    out = yaml.dump(draft_gen.reference)
    if output:
        with open(output, "w") as f:
            f.write(out)
    else:
        print(out)
