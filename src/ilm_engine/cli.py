"""Command-line interface (`ilm-engine`)."""

import typer

from ilm_engine import __version__

app = typer.Typer(help="Post-OCR knowledge enrichment for digitized Islamic books.", no_args_is_help=True)


@app.callback()
def main() -> None:
    """ILM Engine command-line interface."""


@app.command()
def version() -> None:
    """Print the package version."""
    typer.echo(__version__)
