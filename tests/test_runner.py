from collections import Counter
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ilm_engine.cli import app
from ilm_engine.config import load_config
from ilm_engine.pipeline.runner import PipelineError, RunContext, Runner, Step, StepRegistry, StepResult
from ilm_engine.pipeline.steps import PIPELINE, STEP_NAMES, build_registry

PUB_REF = "pub_TEST@r1"


@pytest.fixture
def inputs(tmp_path: Path) -> dict[str, Path]:
    source = tmp_path / "book.json"
    source.write_text('{"pub": {"id": "pub_TEST"}}', encoding="utf-8")
    return {"json": source}


def counting_registry(calls: Counter) -> StepRegistry:
    """The real 21-step graph with stand-in functions that count calls and write their outputs."""
    registry = build_registry()
    for name in registry.names():
        step = registry[name]

        def fn(ctx: RunContext, step: Step = step) -> StepResult:
            calls[step.name] += 1
            if step.name == "adapt":
                ctx.pub_ref = PUB_REF
            return StepResult(
                files={output: {"step": step.name} for output in step.outputs}, data={"x": step.name}
            )

        registry.replace(name, fn)
    return registry


def run(registry, inputs, tmp_path, config=None, **options):
    ctx = RunContext(config=config or load_config(), inputs=inputs, out_root=tmp_path / "out")
    return Runner(registry, cache_dir=tmp_path / "cache").run(ctx, **options), ctx


def statuses(records) -> dict[str, str]:
    return {record.name: record.status for record in records}


def test_registry_has_the_21_steps_in_order():
    assert PIPELINE.names() == list(STEP_NAMES)
    assert len(STEP_NAMES) == 21


def test_first_run_executes_every_step_and_writes_outputs(inputs, tmp_path):
    calls = Counter()
    records, ctx = run(counting_registry(calls), inputs, tmp_path)
    assert set(statuses(records).values()) == {"ran"} and len(records) == 21
    assert all(count == 1 for count in calls.values())
    assert ctx.store.read("validation_report.json") == {"step": "validate"}
    assert ctx.data("units", "x") == "units"


def test_second_run_without_changes_executes_no_step(inputs, tmp_path):
    calls = Counter()
    registry = counting_registry(calls)
    run(registry, inputs, tmp_path)
    records, ctx = run(registry, inputs, tmp_path)
    assert set(statuses(records).values()) == {"cached"}
    assert sum(calls.values()) == 21
    assert ctx.pub_ref == PUB_REF and ctx.data("relations", "x") == "relations"


def test_threshold_change_reruns_only_validation_and_downstream(inputs, tmp_path):
    calls = Counter()
    registry = counting_registry(calls)
    run(registry, inputs, tmp_path)
    changed = load_config().model_copy(
        update={
            "review": load_config().review.model_copy(
                update={"threshold": load_config().review.threshold.model_copy(update={"default": 0.9})}
            )
        }
    )
    records, _ = run(registry, inputs, tmp_path, config=changed)
    rerun = [name for name, status in statuses(records).items() if status == "ran"]
    assert rerun == ["validate", "review_queue", "store", "export", "integrity_verify", "manifest"]


def test_input_change_reruns_everything(inputs, tmp_path):
    registry = counting_registry(Counter())
    run(registry, inputs, tmp_path)
    inputs["json"].write_text('{"pub": {"id": "pub_TEST"}, "changed": true}', encoding="utf-8")
    records, _ = run(registry, inputs, tmp_path)
    assert set(statuses(records).values()) == {"ran"}


def test_deleted_output_file_reruns_its_step(inputs, tmp_path):
    registry = counting_registry(Counter())
    _, ctx = run(registry, inputs, tmp_path)
    ctx.store.path("citations.json").unlink()
    records, _ = run(registry, inputs, tmp_path)
    assert statuses(records)["citations"] == "ran" and statuses(records)["annotations"] == "cached"


def test_no_cache_reruns_everything(inputs, tmp_path):
    registry = counting_registry(Counter())
    run(registry, inputs, tmp_path)
    records, _ = run(registry, inputs, tmp_path, no_cache=True)
    assert set(statuses(records).values()) == {"ran"}


def test_from_step_reruns_it_and_downstream(inputs, tmp_path):
    registry = counting_registry(Counter())
    run(registry, inputs, tmp_path)
    records, _ = run(registry, inputs, tmp_path, from_step="entities")
    rerun = [name for name, status in statuses(records).items() if status == "ran"]
    assert rerun[0] == "entities" and "units" not in rerun and "relations" in rerun and "manifest" in rerun


def test_only_runs_one_step_with_cached_upstream(inputs, tmp_path):
    calls = Counter()
    registry = counting_registry(calls)
    run(registry, inputs, tmp_path)
    records, _ = run(registry, inputs, tmp_path, only="citations")
    assert statuses(records) == {
        "ingest": "cached",
        "adapt": "cached",
        "structure": "cached",
        "origin": "cached",
        "annotations": "cached",
        "citations": "ran",
    }


def test_unknown_step_option_rejected(inputs, tmp_path):
    with pytest.raises(ValueError, match="unknown step"):
        run(counting_registry(Counter()), inputs, tmp_path, only="nope")


def test_placeholder_steps_are_reported_skipped(inputs, tmp_path):
    records, _ = run(build_registry(), inputs, tmp_path)
    assert set(statuses(records).values()) == {"skipped"}


def test_failure_raises_with_records(inputs, tmp_path):
    registry = counting_registry(Counter())

    def broken(ctx):
        raise RuntimeError("boom")

    registry.replace("structure", broken)
    with pytest.raises(PipelineError, match="structure") as caught:
        run(registry, inputs, tmp_path)
    assert caught.value.records[-1].name == "structure" and caught.value.records[-1].status == "failed"


def test_retries(inputs, tmp_path):
    attempts = Counter()

    def flaky(ctx):
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise RuntimeError("transient")
        return StepResult()

    registry = StepRegistry([Step("flaky", flaky, retries=1)])
    records, _ = run(registry, inputs, tmp_path)
    assert records[0].status == "ran" and attempts["n"] == 2


def test_undeclared_output_rejected(inputs, tmp_path):
    registry = StepRegistry([Step("a", lambda ctx: StepResult(files={"entities.json": []}))])
    with pytest.raises(PipelineError, match="undeclared outputs"):
        run(registry, inputs, tmp_path)


def test_registry_validation():
    registry = StepRegistry([Step("a", lambda ctx: StepResult())])
    with pytest.raises(ValueError, match="already registered"):
        registry.add(Step("a", lambda ctx: StepResult()))
    with pytest.raises(ValueError, match="unregistered"):
        registry.add(Step("b", lambda ctx: StepResult(), needs=("missing",)))


def test_cli_list_steps():
    result = CliRunner().invoke(app, ["run", "--list-steps"])
    assert result.exit_code == 0
    assert result.output.split() == list(STEP_NAMES)
