"""In-process DAG runner (ADR-004). Each step maps 1:1 to a Prefect task in production.

A step runs in topological order with the cache key
`sha256(name + version + config sections it reads + upstream cache keys + input file hashes)`.
If an entry with that key exists and the step's output files are unchanged, the step is not executed
(`cached`) and its stored result is reused, so a rerun without changes executes no step, and a config
change re-runs only the steps that read the changed section plus everything downstream.
"""

from __future__ import annotations

import hashlib
import pickle
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from ilm_engine.config import Config
from ilm_engine.enrichment.models import Issue, StepRecord
from ilm_engine.integrity.hashing import canonical_json, file_sha256
from ilm_engine.log import get_logger, log_context
from ilm_engine.storage.json_store import JsonStore, write_bytes_atomic

log = get_logger("pipeline.runner")

DEFAULT_CACHE_DIR = Path(".cache") / "steps"

StepStatus = Literal["ran", "cached", "skipped", "failed"]


@dataclass
class StepResult:
    files: dict[str, Any] = field(default_factory=dict)  # output file name (DECISIONS §10) → object
    data: dict[str, Any] = field(default_factory=dict)  # in-memory values for downstream steps
    issues: list[Issue] = field(default_factory=list)
    skipped: bool = False  # the step had nothing to do (e.g. not implemented yet)


@dataclass
class RunContext:
    config: Config
    inputs: dict[str, Path]  # e.g. {"json": ..., "pdf": ...}
    out_root: Path = Path("output")
    llm: Any = None  # LLMGateway
    options: dict[str, Any] = field(default_factory=dict)
    pub_ref: str | None = None  # set by the `adapt` step
    results: dict[str, StepResult] = field(default_factory=dict)

    def data(self, step: str, key: str) -> Any:
        """A value produced by an upstream step."""
        try:
            return self.results[step].data[key]
        except KeyError:
            raise KeyError(f"step {step!r} produced no {key!r}") from None

    @property
    def store(self) -> JsonStore:
        if self.pub_ref is None:
            raise RuntimeError("pub_ref is not known yet (set by the adapt step)")
        return JsonStore(self.pub_ref, self.out_root)


StepFn = Callable[[RunContext], StepResult]


@dataclass(frozen=True)
class Step:
    name: str
    fn: StepFn
    version: str = "1.0.0"
    needs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()  # files written by the runner from StepResult.files
    config: tuple[str, ...] = ()  # config sections the step reads (part of its cache key)
    uses_inputs: bool = False  # input file hashes are part of the cache key
    retries: int = 0


class PipelineError(RuntimeError):
    def __init__(self, step: str, records: list[StepRecord], cause: BaseException) -> None:
        super().__init__(f"step {step!r} failed: {cause}")
        self.step = step
        self.records = records


class StepRegistry:
    def __init__(self, steps: Iterable[Step] = ()) -> None:
        self._steps: dict[str, Step] = {}
        for step in steps:
            self.add(step)

    def add(self, step: Step) -> Step:
        if step.name in self._steps:
            raise ValueError(f"step {step.name!r} is already registered")
        unknown = [need for need in step.needs if need not in self._steps]
        if unknown:
            raise ValueError(f"step {step.name!r} needs unregistered step(s): {', '.join(unknown)}")
        self._steps[step.name] = step
        return step

    def replace(self, name: str, fn: StepFn, version: str | None = None) -> None:
        """Swap in the implementation of a registered step (keeps its position and dependencies)."""
        current = self._steps[name]
        self._steps[name] = Step(
            name=current.name,
            fn=fn,
            version=version or current.version,
            needs=current.needs,
            outputs=current.outputs,
            config=current.config,
            uses_inputs=current.uses_inputs,
            retries=current.retries,
        )

    def names(self) -> list[str]:
        """Step names in registration order, which is a valid topological order."""
        return list(self._steps)

    def __getitem__(self, name: str) -> Step:
        return self._steps[name]

    def downstream(self, name: str) -> list[str]:
        """`name` and every step that depends on it, in order."""
        selected = {name}
        for step in self._steps.values():
            if any(need in selected for need in step.needs):
                selected.add(step.name)
        return [step for step in self._steps if step in selected]

    def upstream(self, name: str) -> list[str]:
        """Every step `name` depends on, transitively, in order."""
        needed: set[str] = set()
        pending = list(self._steps[name].needs)
        while pending:
            current = pending.pop()
            if current not in needed:
                needed.add(current)
                pending.extend(self._steps[current].needs)
        return [step for step in self._steps if step in needed]


def _config_section_hash(config: Config, sections: tuple[str, ...]) -> str:
    dumped = config.model_dump(mode="json", by_alias=True)
    values = {}
    for path in sections:
        value: Any = dumped
        for part in path.split("."):
            value = value[part]
        values[path] = value
    return hashlib.sha256(canonical_json(values)).hexdigest()


class Runner:
    def __init__(self, registry: StepRegistry, cache_dir: str | Path = DEFAULT_CACHE_DIR) -> None:
        self.registry = registry
        self.cache_dir = Path(cache_dir)

    def cache_key(self, step: Step, ctx: RunContext, upstream_keys: dict[str, str]) -> str:
        parts: dict[str, Any] = {
            "step": step.name,
            "version": step.version,
            "config": _config_section_hash(ctx.config, step.config),
            "needs": {need: upstream_keys[need] for need in step.needs},
        }
        if step.uses_inputs:
            parts["inputs"] = {name: file_sha256(path) for name, path in sorted(ctx.inputs.items())}
        return hashlib.sha256(canonical_json(parts)).hexdigest()

    def run(
        self,
        ctx: RunContext,
        only: str | None = None,
        from_step: str | None = None,
        no_cache: bool = False,
    ) -> list[StepRecord]:
        """Run the pipeline; returns one `StepRecord` per executed or reused step."""
        names = self.registry.names()
        forced: set[str] = set(names) if no_cache else set()
        selected = names
        if from_step is not None:
            self._check(from_step)
            forced |= set(self.registry.downstream(from_step))
        if only is not None:
            self._check(only)
            forced.add(only)
            selected = [*self.registry.upstream(only), only]

        records: list[StepRecord] = []
        keys: dict[str, str] = {}
        for name in selected:
            step = self.registry[name]
            key = self.cache_key(step, ctx, keys)
            keys[name] = key
            with log_context(step=name, pub_ref=ctx.pub_ref):
                record = self._run_step(step, ctx, key, force=name in forced, records=records)
            records.append(record)
        return records

    def _check(self, name: str) -> None:
        if name not in self.registry.names():
            raise ValueError(f"unknown step {name!r}; steps: {', '.join(self.registry.names())}")

    def _cache_path(self, step: Step, key: str) -> Path:
        return self.cache_dir / step.name / f"{key}.pkl"

    def _load_cached(self, step: Step, ctx: RunContext, key: str) -> tuple[StepResult, str | None] | None:
        path = self._cache_path(step, key)
        if not path.is_file():
            return None
        try:
            entry = pickle.loads(path.read_bytes())  # local cache written by this runner only
        except Exception:
            return None
        pub_ref = entry.get("pub_ref")
        for name, digest in entry.get("file_hashes", {}).items():
            output = JsonStore(pub_ref, ctx.out_root).path(name) if pub_ref else None
            if output is None or not output.is_file() or file_sha256(output) != digest:
                return None
        return entry["result"], pub_ref

    def _run_step(
        self, step: Step, ctx: RunContext, key: str, force: bool, records: list[StepRecord]
    ) -> StepRecord:
        started = time.monotonic()
        if not force:
            cached = self._load_cached(step, ctx, key)
            if cached is not None:
                result, pub_ref = cached
                ctx.results[step.name] = result
                ctx.pub_ref = ctx.pub_ref or pub_ref
                log.debug("step cached", extra={"cache_key": key})
                return self._record(step, "cached", key, started, result)

        attempts = step.retries + 1
        for attempt in range(1, attempts + 1):
            try:
                result = step.fn(ctx)
                break
            except Exception as exc:
                if attempt == attempts:
                    log.exception("step failed")
                    records.append(self._record(step, "failed", key, started, StepResult()))
                    raise PipelineError(step.name, records, exc) from exc
                log.warning("step failed, retrying", extra={"attempt": attempt, "error": str(exc)})

        unexpected = set(result.files) - set(step.outputs)
        if unexpected:
            raise PipelineError(step.name, records, ValueError(f"undeclared outputs: {sorted(unexpected)}"))
        file_hashes = {
            name: file_sha256(ctx.store.write(name, obj)) for name, obj in sorted(result.files.items())
        }
        ctx.results[step.name] = result
        entry = {"result": result, "pub_ref": ctx.pub_ref, "file_hashes": file_hashes}
        write_bytes_atomic(self._cache_path(step, key), pickle.dumps(entry))
        status: StepStatus = "skipped" if result.skipped else "ran"
        log.info(f"step {status}", extra={"duration_ms": int((time.monotonic() - started) * 1000)})
        return self._record(step, status, key, started, result)

    @staticmethod
    def _record(step: Step, status: StepStatus, key: str, started: float, result: StepResult) -> StepRecord:
        return StepRecord(
            name=step.name,
            version=step.version,
            status=status,
            cache_key=key,
            duration_ms=int((time.monotonic() - started) * 1000),
            outputs=sorted(result.files),
        )
