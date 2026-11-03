"""Command-line interface (`ilm-engine`).

Exit codes: 0 ok, 1 pipeline or validation failure, 2 unknown source schema (fail closed).
"""

import json
from pathlib import Path
from typing import Annotated

import typer

from ilm_engine import __version__
from ilm_engine.config import load_config
from ilm_engine.log import logging_setup

app = typer.Typer(help="Post-OCR knowledge enrichment for digitized Islamic books.", no_args_is_help=True)
schema_app = typer.Typer(help="Contract JSON Schemas.", no_args_is_help=True)
app.add_typer(schema_app, name="schema")

EXIT_OK, EXIT_FAILED, EXIT_UNKNOWN_SCHEMA = 0, 1, 2
LLM_PROVIDERS = ("null", "fixture", "anthropic", "litellm")


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
    input: Annotated[
        Path | None, typer.Option("--input", help="Source JSON file, or a folder with one.")
    ] = None,
    pdf: Annotated[
        Path | None, typer.Option("--pdf", help="Scan PDF (default: _meta.scan.saved_file).")
    ] = None,
    llm: Annotated[str | None, typer.Option("--llm", help="null | fixture | anthropic | litellm.")] = None,
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
    store_root: Annotated[Path, typer.Option("--store", help="Read-only original store root.")] = Path(
        "store/originals"
    ),
    cache_dir: Annotated[Path, typer.Option("--cache-dir", help="Step and LLM cache root.")] = Path(".cache"),
) -> None:
    """Run the enrichment pipeline on one book."""
    from ilm_engine.adapters.registry import UnknownSchemaError
    from ilm_engine.llm.cache import ResponseCache
    from ilm_engine.llm.gateway import LLMGateway, get_provider
    from ilm_engine.pipeline.runner import PipelineError, RunContext, Runner
    from ilm_engine.pipeline.stages import find_inputs
    from ilm_engine.pipeline.steps import PIPELINE

    if list_steps:
        for name in PIPELINE.names():
            typer.echo(name)
        return
    if input is None:
        raise typer.BadParameter("--input is required", param_hint="--input")
    if llm is not None and llm not in LLM_PROVIDERS:
        raise typer.BadParameter(f"must be one of {', '.join(LLM_PROVIDERS)}", param_hint="--llm")

    inputs = find_inputs(input, pdf)
    raw = json.loads(inputs["json"].read_text(encoding="utf-8"))
    pub_id = raw.get("pub", {}).get("id") if isinstance(raw.get("pub"), dict) else None
    config = load_config(pub_id)
    provider_name = llm or config.llm.provider
    if provider_name in ("anthropic", "litellm"):
        route = config.llm.extractor
        extra = {"api_base": route.api_base} if provider_name == "litellm" and route.api_base else {}
        provider = get_provider(provider_name, default_model=route.model, **extra)
    else:
        provider = get_provider(provider_name)
    gateway = LLMGateway(provider, temperature=config.llm.temperature, cache=ResponseCache(cache_dir / "llm"))

    ctx = RunContext(
        config=config,
        inputs=inputs,
        out_root=out,
        llm=gateway,
        options={"llm": provider_name, "store_root": store_root},
    )
    try:
        runner = Runner(PIPELINE, cache_dir=cache_dir / "steps")
        records = runner.run(ctx, only=only, from_step=from_step, no_cache=no_cache)
    except PipelineError as error:
        for record in error.records:
            typer.echo(f"{record.status:<8} {record.name}")
        typer.echo(f"error: {error}", err=True)
        cause = error.__cause__
        raise typer.Exit(
            EXIT_UNKNOWN_SCHEMA if isinstance(cause, UnknownSchemaError) else EXIT_FAILED
        ) from None
    for record in records:
        typer.echo(f"{record.status:<8} {record.name}")
    if ctx.pub_ref:
        typer.echo(f"output: {ctx.store.directory}")


@app.command()
def verify(
    out_dir: Annotated[Path, typer.Argument(help="Output folder of a run: output/<pub_ref>.")],
    store_root: Annotated[Path, typer.Option("--store", help="Original store root.")] = Path(
        "store/originals"
    ),
) -> None:
    """Check a run's integrity: output and input hashes match the manifest, originals unchanged."""
    from ilm_engine.enrichment.models import RunManifest
    from ilm_engine.integrity import store as original_store
    from ilm_engine.integrity.hashing import file_sha256

    manifest_path = out_dir / "run_manifest.json"
    if not manifest_path.is_file():
        typer.echo(f"FAIL no run_manifest.json in {out_dir}", err=True)
        raise typer.Exit(EXIT_FAILED)
    manifest = RunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    problems = []
    for item in manifest.outputs:
        path = out_dir / item.path
        if not path.is_file() or file_sha256(path) != item.sha256:
            problems.append(f"output changed or missing: {item.path}")
    for item in manifest.inputs:
        path = Path(item.path)
        if not path.is_file() or file_sha256(path) != item.sha256:
            problems.append(f"input changed or missing: {item.path}")
    if not original_store.verify(manifest.pub_ref, store_root):
        problems.append(f"original store check failed for {manifest.pub_ref}")
    if manifest.integrity.get("originals_unchanged") is False or manifest.integrity.get("stale", 0):
        problems.append("the run recorded integrity problems (see run_manifest.json integrity)")
    for problem in problems:
        typer.echo(f"FAIL {problem}", err=True)
    if problems:
        raise typer.Exit(EXIT_FAILED)
    typer.echo(
        f"OK {manifest.pub_ref}: {len(manifest.outputs)} outputs, {len(manifest.inputs)} inputs verified"
    )


@schema_app.command("export")
def schema_export(
    out: Annotated[Path, typer.Option("--out", help="Destination folder.")] = Path("schemas"),
) -> None:
    """Write one JSON Schema per top-level contract model."""
    from ilm_engine.schema_export import export

    for path in export(out):
        typer.echo(str(path))
