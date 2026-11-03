"""Command-line interface (`ilm-engine`)."""

import json
from pathlib import Path
from typing import Annotated

import typer

from ilm_engine import __version__
from ilm_engine.config import load_config
from ilm_engine.log import logging_setup

app = typer.Typer(help="Post-OCR knowledge enrichment for digitized Islamic books.", no_args_is_help=True)


@app.callback()
def main(
    log_json: Annotated[bool, typer.Option("--log-json", help="Write logs as JSON lines to stderr.")] = False,
    log_level: Annotated[str, typer.Option("--log-level", help="DEBUG, INFO, WARNING or ERROR.")] = "INFO",
) -> None:
    """ILM Engine command-line interface."""
    logging_setup(log_level, json=log_json)


@app.command()
def version() -> None:
    """Print the package version."""
    typer.echo(__version__)


@app.command()
def run(
    input: Annotated[Path | None, typer.Option("--input", help="Source JSON file.")] = None,
    out: Annotated[Path, typer.Option("--out", help="Output root; files go to <out>/<pub_ref>/.")] = Path(
        "output"
    ),
    only: Annotated[
        str | None, typer.Option("--only", help="Run only this step (cached upstream reused).")
    ] = None,
    from_step: Annotated[
        str | None, typer.Option("--from", help="Re-run this step and all downstream.")
    ] = None,
    no_cache: Annotated[bool, typer.Option("--no-cache", help="Ignore cached step results.")] = False,
    list_steps: Annotated[
        bool, typer.Option("--list-steps", help="Print the steps in order and exit.")
    ] = False,
) -> None:
    """Run the enrichment pipeline on one book."""
    from ilm_engine.pipeline.runner import RunContext, Runner
    from ilm_engine.pipeline.steps import PIPELINE

    if list_steps:
        for name in PIPELINE.names():
            typer.echo(name)
        return
    if input is None:
        raise typer.BadParameter("--input is required", param_hint="--input")
    raw = json.loads(input.read_text(encoding="utf-8"))
    pub_id = raw.get("pub", {}).get("id") if isinstance(raw.get("pub"), dict) else None
    ctx = RunContext(config=load_config(pub_id), inputs={"json": input}, out_root=out)
    records = Runner(PIPELINE).run(ctx, only=only, from_step=from_step, no_cache=no_cache)
    for record in records:
        typer.echo(f"{record.status:<8} {record.name}")
