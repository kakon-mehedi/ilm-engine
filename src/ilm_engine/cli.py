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
dev_app = typer.Typer(help="Developer-only commands.", no_args_is_help=True)
app.add_typer(dev_app, name="dev")
review_app = typer.Typer(help="Human review of uncertain and sensitive items.", no_args_is_help=True)
app.add_typer(review_app, name="review")

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


@dev_app.command("regen-goldens")
def regen_goldens(
    yes: Annotated[bool, typer.Option("--yes", help="Confirm: overwrite the adapter golden files.")] = False,
) -> None:
    """Regenerate the adapter golden files from the sample (only on explicit request)."""
    from ilm_engine.tools.update_golden import regenerate

    if not yes:
        typer.echo("Refusing to overwrite golden files without --yes.", err=True)
        raise typer.Exit(EXIT_FAILED)
    for path in regenerate():
        typer.echo(str(path))


@review_app.command("apply")
def review_apply(
    decisions: Annotated[Path, typer.Argument(help="review_decisions.json written by a reviewer.")],
    book: Annotated[str, typer.Option("--book", help="pub_ref of the run, e.g. pub_…@r6.")],
    out: Annotated[Path, typer.Option("--out", help="Output root.")] = Path("output"),
) -> None:
    """Apply reviewer decisions: statuses, audit trail, training examples."""
    from ilm_engine.validation.review_queue import ReviewError, apply_decisions, load_decisions

    try:
        summary = apply_decisions(out / book, load_decisions(decisions))
    except ReviewError as error:
        typer.echo(f"error: {error}", err=True)
        raise typer.Exit(EXIT_FAILED) from None
    typer.echo(f"applied {summary['applied']} decisions; {summary['training_examples']} training examples")


@review_app.command("html")
def review_html(
    book: Annotated[str, typer.Option("--book", help="pub_ref of the run.")],
    out: Annotated[Path, typer.Option("--out", help="Output root.")] = Path("output"),
    source: Annotated[Path, typer.Option("--input", help="Source JSON of the book.")] = Path("data"),
) -> None:
    """Re-render review.html from review_queue.json."""
    from ilm_engine.adapters.registry import resolve
    from ilm_engine.enrichment.models import ReviewItem
    from ilm_engine.pipeline.stages import find_inputs
    from ilm_engine.storage.json_store import write_bytes_atomic
    from ilm_engine.validation.review_html import render

    inputs = find_inputs(source)
    raw = json.loads(inputs["json"].read_text(encoding="utf-8"))
    canonical = resolve(raw).to_canonical(raw, inputs.get("pdf"))
    items = [
        ReviewItem.model_validate(i)
        for i in json.loads((out / book / "review_queue.json").read_text(encoding="utf-8"))
    ]
    pdf = inputs.get("pdf")
    path = write_bytes_atomic(
        out / book / "review.html", render(canonical, items, str(pdf.resolve()) if pdf else None).encode()
    )
    typer.echo(str(path))


@app.command("rebuild-derived")
def rebuild_derived_command(
    out_dir: Annotated[Path, typer.Argument(help="Output folder of a run: output/<pub_ref>.")],
    store_root: Annotated[Path, typer.Option("--store", help="Original store root.")] = Path(
        "store/originals"
    ),
) -> None:
    """Rebuild search_index.json, graph.html and graph.cypher from enrichment.db and the originals."""
    from ilm_engine.storage.derived import rebuild_derived

    for path in rebuild_derived(out_dir, store_root):
        typer.echo(str(path))


def _book_dir(out: Path, book: str | None) -> Path:
    if book:
        return out / book
    runs = sorted(path for path in out.glob("*@r*") if (path / "search_index.json").is_file())
    if len(runs) != 1:
        raise typer.BadParameter(f"pass --book (found {len(runs)} runs in {out})", param_hint="--book")
    return runs[0]


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Arabic query; spelling and diacritics are normalized.")],
    book: Annotated[
        str | None, typer.Option("--book", help="pub_ref (default: the only run in --out).")
    ] = None,
    out: Annotated[Path, typer.Option("--out", help="Output root.")] = Path("output"),
    limit: Annotated[int, typer.Option("--limit", help="Number of results.")] = 10,
    semantic: Annotated[
        bool, typer.Option("--semantic", help="Hybrid BM25 + BGE-M3 (semantic extra).")
    ] = False,
) -> None:
    """Search a processed book; prints page, block, origin and the matching text."""
    from ilm_engine.search.lexical import search as lexical_search
    from ilm_engine.search.semantic import hybrid_search

    directory = _book_dir(out, book)
    index = json.loads((directory / "search_index.json").read_text(encoding="utf-8"))
    origins_path = directory / "origin_map.json"
    origins = json.loads(origins_path.read_text(encoding="utf-8"))["blocks"] if origins_path.is_file() else {}
    hits = hybrid_search(index, query, limit) if semantic else lexical_search(index, query, limit)
    if not hits:
        typer.echo("no results")
        raise typer.Exit(EXIT_OK)
    for rank, hit in enumerate(hits, 1):
        anchor = hit.anchor or {}
        origin = origins.get(anchor.get("block_id", ""), "-")
        typer.echo(
            f"{rank:>2}. {hit.kind:<6} p.{anchor.get('page', '?'):<3} {anchor.get('block_id', '-'):<8} "
            f"{origin:<18} {hit.score:7.3f}  {anchor.get('quote', '')}"
        )
