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
):
    draft_gen = DraftGenerator(csv_file=csv_file)
    out = yaml.dump(draft_gen.schema)
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
