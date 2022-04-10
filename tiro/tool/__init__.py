from typer import Typer

from . import schema
from . import mock
from . import validate

app = Typer()

app.add_typer(schema.app, name="schema")
app.add_typer(mock.app, name="mock")
app.add_typer(validate.app, name="validate")
