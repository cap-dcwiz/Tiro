from typer import Typer

from . import schema
from . import mock
from . import validate
from . import draft

app = Typer()

app.add_typer(schema.app, name="schema")
app.add_typer(mock.app, name="mock")
app.add_typer(validate.app, name="validate")
app.add_typer(draft.app, name="draft")
