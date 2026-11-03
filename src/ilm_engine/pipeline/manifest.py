"""Run manifest `run_manifest.json`: the provenance of one run (DECISIONS §10, ADR-011).

It records what produced the outputs (code version, config hash, schema/adapter/normalizer versions,
LLM models and prompt versions), what went in (input file hashes) and what came out (output file
hashes), plus per-step status, cache key and timing. The run ID is deterministic; timestamps appear
only here, never in content files.
"""

from __future__ import annotations

import hashlib
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ilm_engine.canonical.models import CANONICAL_SCHEMA_VERSION
from ilm_engine.config import Config
from ilm_engine.enrichment.models import ENRICHMENT_SCHEMA_VERSION, FileHash, RunManifest, StepRecord
from ilm_engine.ids import make_id, natural_key
from ilm_engine.integrity.hashing import file_sha256
from ilm_engine.llm.prompts import available
from ilm_engine.nlp.normalize import NORMALIZER_VERSION
from ilm_engine.pipeline.runner import RunContext, StepResult

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_FILE = "run_manifest.json"


def code_version(repo: Path = REPO_ROOT) -> str:
    """Git commit SHA, or `dirty-<hash>` when tracked files have uncommitted changes."""
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()
        diff = subprocess.run(["git", "diff", "HEAD"], cwd=repo, capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    if diff:
        return f"dirty-{sha[:12]}-{hashlib.sha256(diff).hexdigest()[:12]}"
    return sha


def file_hash(path: Path, name: str | None = None) -> FileHash:
    return FileHash(path=name or str(path), sha256=file_sha256(path), bytes=path.stat().st_size)


def llm_info(config: Config) -> dict[str, Any]:
    llm = config.llm
    models = [llm.extractor.model] + ([llm.verifier.model] if llm.verifier else [])
    return {
        "provider": llm.provider,
        "routes": {
            "extractor": llm.extractor.model_dump(),
            "verifier": llm.verifier.model_dump() if llm.verifier else None,
        },
        "models": models if llm.provider in ("anthropic", "litellm") else [],
        "prompts": {task: versions[-1] for task, versions in sorted(available().items())},
    }


def run_id(ctx: RunContext, code: str | None = None) -> str:
    """Deterministic run ID: `run` + `config_hash|input hashes|code version` (ADR-011)."""
    if ctx.pub_ref is None:
        raise RuntimeError("run_id needs pub_ref (set by the adapt step)")
    input_key = "|".join(file_sha256(path) for _, path in sorted(ctx.inputs.items()))
    return make_id("run", ctx.pub_ref, natural_key(ctx.config.config_hash, input_key, code or code_version()))


def build_manifest(
    ctx: RunContext,
    steps: list[StepRecord],
    finished_at: str | None = None,
    code: str | None = None,
) -> RunManifest:
    if ctx.pub_ref is None:
        raise RuntimeError("cannot build a run manifest before the adapt step set pub_ref")
    code = code or code_version()
    inputs = [file_hash(path) for _, path in sorted(ctx.inputs.items())]
    outputs = [file_hash(path, path.name) for path in ctx.store.files() if path.name != MANIFEST_FILE]

    adapter: dict[str, str] = {}
    counts: dict[str, int] = {}
    integrity: dict[str, Any] = {}
    for result in ctx.results.values():
        adapter.update(result.data.get("adapter", {}))
        counts.update(result.data.get("counts", {}))
        integrity.update(result.data.get("integrity", {}))

    return RunManifest(
        run_id=run_id(ctx, code),
        pub_ref=ctx.pub_ref,
        started_at=ctx.started_at,
        finished_at=finished_at or datetime.now(UTC).isoformat(timespec="seconds"),
        code_version=code,
        config_hash=ctx.config.config_hash,
        canonical_schema_version=CANONICAL_SCHEMA_VERSION,
        enrichment_schema_version=ENRICHMENT_SCHEMA_VERSION,
        normalizer_version=NORMALIZER_VERSION,
        adapter=adapter,
        llm=llm_info(ctx.config),
        steps=steps,
        inputs=inputs,
        outputs=outputs,
        integrity=integrity,
        counts=dict(sorted(counts.items())),
    )


def manifest_step(ctx: RunContext) -> StepResult:
    """The pipeline's last step: write `run_manifest.json`."""
    if ctx.pub_ref is None:
        return StepResult(skipped=True)
    return StepResult(files={MANIFEST_FILE: build_manifest(ctx, list(ctx.records))})
