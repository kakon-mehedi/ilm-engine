from pathlib import Path

import pytest

from ilm_engine.config import load_config
from ilm_engine.pipeline.narration import STORIES, Narrator
from ilm_engine.pipeline.runner import RunContext, Runner, Step, StepRegistry, StepResult
from ilm_engine.pipeline.steps import STEP_NAMES, build_registry


@pytest.fixture
def inputs(tmp_path: Path) -> dict[str, Path]:
    source = tmp_path / "book.json"
    source.write_text('{"pub": {"id": "pub_TEST"}}', encoding="utf-8")
    return {"json": source}


def stub_registry() -> StepRegistry:
    """The real 21-step graph with stand-ins that write their declared outputs."""
    registry = build_registry()
    for name in registry.names():
        step = registry[name]

        def fn(ctx: RunContext, step: Step = step) -> StepResult:
            if step.name == "adapt":
                ctx.pub_ref = "pub_TEST@r1"
            return StepResult(files={output: {} for output in step.outputs})

        registry.replace(name, fn)
    return registry


def narrate(registry, inputs, tmp_path, **options) -> list[str]:
    lines: list[str] = []
    ctx = RunContext(config=load_config(), inputs=inputs, out_root=tmp_path / "out")
    Runner(registry, cache_dir=tmp_path / "cache").run(ctx, listener=Narrator(lines.append), **options)
    return lines


def test_every_step_has_a_story():
    assert set(STORIES) == set(STEP_NAMES)


def test_two_lines_per_step_and_one_header_per_phase(inputs, tmp_path):
    lines = narrate(stub_registry(), inputs, tmp_path)
    steps = [line for line in lines if line.startswith("Pipeline_")]
    headers = [line for line in lines if line.startswith("\n━━")]
    assert len(steps) == 2 * len(STEP_NAMES)
    assert len(headers) == len({story.phase for story in STORIES.values()})
    assert steps[0] == "Pipeline_01/21 ▶ Ingest: Reading the book JSON and locating the PDF scan..."
    assert (
        steps[1].startswith("Pipeline_01/21 ✓ Got the input: book.json") and "Moving to Adapter →" in steps[1]
    )
    assert steps[-1].endswith("Done.")


def test_cached_steps_are_marked(inputs, tmp_path):
    registry = stub_registry()
    narrate(registry, inputs, tmp_path)
    lines = narrate(registry, inputs, tmp_path)
    finished = [line for line in lines if line.startswith("Pipeline_") and "▶" not in line]
    assert all("↺" in line and "(from cache)" in line for line in finished)


def test_summary_error_never_breaks_the_run(inputs, tmp_path):
    # stand-in steps produce none of the data the summaries read: the status is shown instead
    lines = narrate(stub_registry(), inputs, tmp_path)
    assert "Pipeline_05/21 ✓ ran" in "\n".join(lines)


def test_failed_step_is_reported(inputs, tmp_path):
    def boom(ctx: RunContext) -> StepResult:
        raise RuntimeError("boom")

    registry = StepRegistry([Step("ingest", fn=boom, uses_inputs=True)])
    lines: list[str] = []
    ctx = RunContext(config=load_config(), inputs=inputs, out_root=tmp_path / "out")
    try:
        Runner(registry, cache_dir=tmp_path / "cache").run(ctx, listener=Narrator(lines.append))
    except Exception:
        pass
    assert lines[-1] == "Pipeline_01/1 ✗ Ingest failed."
