"""Command-line interface (`ilm-engine`)."""

import typer

from ilm_engine import __version__
from ilm_engine.log import logging_setup

app = typer.Typer(help="Post-OCR knowledge enrichment for digitized Islamic books.", no_args_is_help=True)


@app.callback()
def main(
    log_json: bool = typer.Option(False, "--log-json", help="Write logs as JSON lines to stderr."),
    log_level: str = typer.Option("INFO", "--log-level", help="DEBUG, INFO, WARNING or ERROR."),
) -> None:
    """ILM Engine command-line interface."""
    logging_setup(log_level, json=log_json)


@app.command()
def version() -> None:
    """Print the package version."""
    typer.echo(__version__)
